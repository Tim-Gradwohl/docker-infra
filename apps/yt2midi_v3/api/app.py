import re
import uuid
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_TITLE = "yt2midi API"
DATA_IN = Path("/data/in")
DATA_OUT = Path("/data/out")

app = FastAPI(title=APP_TITLE)

# In-memory job state (good enough for a small single-instance tool)
JOBS: Dict[str, Dict[str, Any]] = {}
LOCK = threading.Lock()


class ProcessRequest(BaseModel):
    url: str = Field(..., examples=["https://www.youtube.com/watch?v=..."])
    device: str = Field("cuda", examples=["cuda", "cpu"])


def _safe_stem(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("._-")
    return name or "output"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def _set(job_id: str, **kwargs):
    with LOCK:
        JOBS.setdefault(job_id, {})
        JOBS[job_id].update(kwargs)


def _append_log(job_id: str, chunk: str, max_chars: int = 20000):
    if not chunk:
        return
    with LOCK:
        j = JOBS.setdefault(job_id, {})
        cur = j.get("logs", "")
        cur = (cur + chunk)
        if len(cur) > max_chars:
            cur = cur[-max_chars:]
        j["logs"] = cur


def _download_mp3(job_id: str, url: str, out_dir: Path) -> tuple[Optional[Path], str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--restrict-filenames",
        "-o", out_template,
        url,
    ]

    _append_log(job_id, "\n$ " + " ".join(cmd) + "\n")
    proc = _run(cmd)
    _append_log(job_id, proc.stdout + "\n")

    if proc.returncode != 0:
        return None, proc.stdout

    mp3s = sorted(out_dir.glob("*.mp3"))
    if not mp3s:
        return None, proc.stdout + "\n\nERROR: download succeeded but no .mp3 found."
    return mp3s[0], proc.stdout


def _transcribe(job_id: str, mp3_path: Path, midi_path: Path, device: str) -> tuple[bool, str]:
    cmd = ["transkun", str(mp3_path), str(midi_path), "--device", device]
    _append_log(job_id, "\n$ " + " ".join(cmd) + "\n")

    proc = _run(cmd)
    _append_log(job_id, proc.stdout + "\n")

    if proc.returncode != 0:
        return False, proc.stdout
    if not midi_path.exists():
        return False, proc.stdout + "\n\nERROR: transkun finished but output .mid not found."
    return True, proc.stdout


def _worker(job_id: str, url: str, device: str):
    try:
        _set(job_id, status="running", stage="starting", progress=5, indeterminate=True, message="Starting…")

        job_in = DATA_IN / job_id
        job_out = DATA_OUT / job_id
        job_out.mkdir(parents=True, exist_ok=True)

        # Download
        _set(job_id, stage="download", progress=10, indeterminate=True, message="Downloading audio (yt-dlp)…")
        mp3_path, _ = _download_mp3(job_id, url, job_in)
        if mp3_path is None:
            _set(job_id, status="error", stage="download", progress=10, indeterminate=False, message="Download failed. Check logs.")
            return

        # Copy MP3 to output and keep original title
        stem = _safe_stem(mp3_path.stem)
        mp3_out = job_out / f"{stem}.mp3"
        mp3_out.write_bytes(mp3_path.read_bytes())
        _set(job_id, stage="transcribe", progress=35, indeterminate=True, message="Transcribing to MIDI (transkun)…")

        midi_out = job_out / f"{stem}.mid"
        ok, _ = _transcribe(job_id, mp3_out, midi_out, device=device)
        if not ok:
            _set(job_id, status="error", stage="transcribe", progress=35, indeterminate=False, message="Transcription failed. Check logs.")
            return

        # Cleanup input scratch
        try:
            for p in job_in.glob("*"):
                p.unlink(missing_ok=True)
            job_in.rmdir()
        except Exception:
            pass

        files = [mp3_out.name, midi_out.name]
        _set(job_id, status="done", stage="done", progress=100, indeterminate=False, message="Done.", files=files)

    except Exception as e:
        _append_log(job_id, f"\nUNHANDLED ERROR: {e}\n")
        _set(job_id, status="error", stage="exception", progress=0, indeterminate=False, message="Unexpected error. Check logs.")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/process")
def process(req: ProcessRequest):
    device = (req.device or "cuda").strip().lower()
    if device not in {"cuda", "cpu"}:
        return {"detail": "Invalid device. Use 'cuda' or 'cpu'."}, 400

    url = (req.url or "").strip()
    if not url:
        return {"detail": "Missing URL."}, 400

    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "indeterminate": True,
            "message": "Queued…",
            "files": [],
            "logs": "",
        }

    t = threading.Thread(target=_worker, args=(job_id, url, device), daemon=True)
    t.start()
    return {"job_id": job_id}


@app.get("/status/{job_id}")
def status(job_id: str):
    job_id = (job_id or "").strip()
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        return {"detail": "Invalid job id."}, 400
    with LOCK:
        j = JOBS.get(job_id)
        if not j:
            return {"detail": "Not found."}, 404
        # shallow copy
        return dict(j)


@app.get("/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    job_id = (job_id or "").strip()
    filename = (filename or "").strip()

    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        return {"detail": "Invalid job id."}, 400
    if "/" in filename or "\\" in filename or ".." in filename:
        return {"detail": "Invalid filename."}, 400

    path = DATA_OUT / job_id / filename
    if not path.exists() or not path.is_file():
        return {"detail": "Not found."}, 404

    media_type = "application/octet-stream"
    if filename.lower().endswith(".mp3"):
        media_type = "audio/mpeg"
    elif filename.lower().endswith(".mid") or filename.lower().endswith(".midi"):
        media_type = "audio/midi"

    return FileResponse(path=str(path), media_type=media_type, filename=filename)

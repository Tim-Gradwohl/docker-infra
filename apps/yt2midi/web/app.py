import re
import uuid
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse

APP_TITLE = "YouTube → MP3 + MIDI (Transkun)"
DATA_IN = Path("/data/in")
DATA_OUT = Path("/data/out")

app = FastAPI(title=APP_TITLE)

# ------------------------
# Helpers
# ------------------------

def _safe_stem(name: str) -> str:
    # Keep filenames boring and safe
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

def _download_mp3(url: str, out_dir: Path) -> tuple[Optional[Path], str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use original YouTube title as filename
    out_template = str(out_dir / "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--restrict-filenames",   # makes titles filesystem-safe
        "-o", out_template,
        url,
    ]

    proc = _run(cmd)
    if proc.returncode != 0:
        return None, proc.stdout

    mp3s = sorted(out_dir.glob("*.mp3"))
    if not mp3s:
        return None, proc.stdout + "\n\nERROR: download succeeded but no .mp3 found."

    return mp3s[0], proc.stdout

def _transcribe(mp3_path: Path, midi_path: Path, device: str) -> tuple[bool, str]:
    cmd = ["transkun", str(mp3_path), str(midi_path), "--device", device]
    proc = _run(cmd)
    if proc.returncode != 0:
        return False, proc.stdout
    if not midi_path.exists():
        return False, proc.stdout + "\n\nERROR: transkun finished but output .mid not found."
    return True, proc.stdout

# ------------------------
# Routes
# ------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{APP_TITLE}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 840px; margin: 2rem auto; padding: 0 1rem; }}
    input[type=text] {{ width: 100%; padding: .6rem; font-size: 1rem; }}
    select {{ padding: .4rem; }}
    button {{ padding: .6rem 1rem; font-size: 1rem; cursor: pointer; }}
    .hint {{ color: #555; }}
    .box {{ background: #f6f7f8; padding: 1rem; border-radius: 12px; }}
    code {{ background: #eee; padding: 0 .25rem; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>{APP_TITLE}</h1>
  <div class="box">
    <form method="post" action="/process">
      <label><b>YouTube URL</b></label><br/>
      <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required /><br/><br/>

      <label><b>Device</b></label><br/>
      <select name="device">
        <option value="cuda" selected>cuda (GPU)</option>
        <option value="cpu">cpu</option>
      </select>
      <p class="hint">This will download audio via <code>yt-dlp</code>, extract MP3, then run <code>transkun</code> to generate MIDI.</p>

      <button type="submit">Generate MP3 + MIDI</button>
    </form>
  </div>

  <p class="hint">
    Files are stored under <code>/data/out/&lt;job-id&gt;/</code> (bind-mounted to your host),
    so you can re-download later.
  </p>
</body>
</html>
"""


@app.post("/process", response_class=HTMLResponse)
def process(
    url: str = Form(...),
    device: str = Form("cuda"),
):
    device = (device or "cuda").strip().lower()
    if device not in {"cuda", "cpu"}:
        return PlainTextResponse("Invalid device. Use 'cuda' or 'cpu'.", status_code=400)

    url = (url or "").strip()
    if not url:
        return PlainTextResponse("Missing URL.", status_code=400)

    job_id = uuid.uuid4().hex
    job_in = DATA_IN / job_id
    job_out = DATA_OUT / job_id
    job_out.mkdir(parents=True, exist_ok=True)

    mp3_path, ytdlp_log = _download_mp3(url, job_in)
    if mp3_path is None:
        return HTMLResponse(
            f"""<h2>Download failed</h2>
<pre>{ytdlp_log}</pre>
<p><a href="/">Back</a></p>""",
            status_code=500,
        )

    
    # Keep original title as base name
    stem = _safe_stem(mp3_path.stem)

    mp3_out = job_out / f"{stem}.mp3"
    mp3_out.write_bytes(mp3_path.read_bytes())

    midi_out = job_out / f"{stem}.mid"
    ok, transkun_log = _transcribe(mp3_out, midi_out, device=device)
    if not ok:
        return HTMLResponse(
            f"""<h2>Transcription failed</h2>
<pre>{transkun_log}</pre>
<p><a href="/">Back</a></p>""",
            status_code=500,
        )

    # Best-effort cleanup of input scratch
    try:
        for p in job_in.glob("*"):
            p.unlink(missing_ok=True)
        job_in.rmdir()
    except Exception:
        pass

    return f"""<!doctype html>
<html>
<head><meta charset="utf-8" /><title>Done - {APP_TITLE}</title></head>
<body style="font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; max-width: 840px; margin: 2rem auto; padding: 0 1rem;">
  <h2>Done ✅</h2>
  <p><b>Job:</b> <code>{job_id}</code></p>
  <ul>
    <li><a href="/download/{job_id}/{mp3_out.name}">Download MP3</a></li>
    <li><a href="/download/{job_id}/{midi_out.name}">Download MIDI</a></li>
  </ul>
  <p><a href="/">Run another</a></p>
</body>
</html>
"""


@app.get("/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    job_id = (job_id or "").strip()
    filename = (filename or "").strip()

    # Basic path safety
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        return PlainTextResponse("Invalid job id.", status_code=400)
    if "/" in filename or "\\" in filename or ".." in filename:
        return PlainTextResponse("Invalid filename.", status_code=400)

    path = DATA_OUT / job_id / filename
    if not path.exists() or not path.is_file():
        return PlainTextResponse("Not found.", status_code=404)

    media_type = "application/octet-stream"
    if filename.lower().endswith(".mp3"):
        media_type = "audio/mpeg"
    elif filename.lower().endswith(".mid") or filename.lower().endswith(".midi"):
        media_type = "audio/midi"

    return FileResponse(path=str(path), media_type=media_type, filename=filename)

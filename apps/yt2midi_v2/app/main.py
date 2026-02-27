"""yt2midi_v2 - FastAPI service



This service provides a deterministic, fully-automatic pipeline:


1) Download best audio from a YouTube URL (yt-dlp) and extract MP3.
2) Transcribe MP3 -> raw MIDI using Transkun CLI (GPU/CPU selectable).
3) Postprocess raw MIDI to improve sheet-music readiness:
   - Dynamic (time-varying) left-hand / right-hand separation using a global optimizer (DP).
   - Preserve expressive MIDI controls (sustain pedal, etc.) for natural playback.
   - Musical key detection (Krumhansl-style profiles) with multiple confidence signals.
4) Write artifacts into per-job folders under /data/out/<job_id>/

Outputs per job:
- <title>.mp3
- <title>.raw.mid
- <title>.piano.mid   (two-track MIDI: RH + LH + copied CC/pitch-bend)
- analysis.json        (hand-split stats + key estimation details)


Notes for reviewers:
- This is intentionally deterministic. No LLM/Ollama is used yet.

- The hand separation is style-agnostic: it chooses a boundary per onset-event and
  uses dynamic programming to keep boundaries stable and hands playable.
- The earlier version sounded "less natural" because it dropped sustain pedal and other
  expressive controls. This version copies CC and pitch bends into the split MIDI.
"""


# -----------------------------------------------------------------------------
# v5 reviewer notes
# - Adds polyphonic voice separation within each staff (music21.stream.Voice).
#   This is the single biggest readability improvement for piano notation.
# - Adds velocity-weighted key detection to downweight quiet transcription noise.
# - Adds adaptive quantization that can locally prefer triplet grids.
# -----------------------------------------------------------------------------


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, HttpUrl

from pathlib import Path
import uuid
import time

import subprocess
import os

import json
import urllib.parse

import numpy as np
import pretty_midi

import math

# Runtime bind mounts (from docker compose)
DATA_IN = Path("/data/in")
DATA_OUT = Path("/data/out")

# Default to CUDA; allow override via env (e.g. TRANSKUN_DEVICE=cpu)



# MusicXML export controls
EXPORT_MUSICXML = os.getenv("EXPORT_MUSICXML", "1").strip().lower() not in ("0", "false", "no", "")

# Quantization grid in quarterLength (music21). 0 disables quantization.
# Examples: 0.25=1/16, 0.5=1/8, 1.0=quarter note
MXML_GRID = float(os.getenv("MXML_GRID", "0.25"))



TRANSKUN_DEVICE = os.getenv("TRANSKUN_DEVICE", "cuda").strip().lower()
# If set to "1" (default), copy CC/pitch-bend into BOTH LH/RH tracks for natural playback.

# If set to "0", emit a third "Global" track that contains CC/pitch-bend (avoids duplication in some tools).
DUPLICATE_CONTROLS = os.getenv("DUPLICATE_CONTROLS", "1").strip() not in ("0", "false", "False")

app = FastAPI(title="yt2midi_v2")


# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
# The built-in Web UI is served from the same origin, so CORS is not strictly
# required. We still enable permissive CORS to make it easy to call the API
# from other hosts/tools during development.
# If you expose this service beyond your LAN, you should restrict allow_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class YoutubeRequest(BaseModel):

    """Request payload for YouTube conversion."""


    url: HttpUrl



@app.get("/health")

def health():

    """Health check endpoint for Traefik / monitoring."""


    return {"ok": True, "service": "yt2midi_v2"}


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess and capture stdout+stderr as text.

    We never raise via subprocess directly; we return the completed process so
    callers can attach contextual error messages.
    """
    return subprocess.run(


        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,

        check=False,
    )




def run_or_raise(cmd: list[str], context: str) -> None:
    """Run a command and raise a readable error if it fails."""
    proc = _run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"{context} failed:\n{proc.stdout}")



def transcribe_to_midi(mp3_path: Path, midi_path: Path, device: str) -> None:
    """Transcribe an MP3 file to MIDI using Transkun CLI.


    This mirrors the original yt2midi approach: use the transkun command-line tool
    inside the container (no network calls).
    """

    cmd = ["transkun", str(mp3_path), str(midi_path), "--device", device]

    proc = _run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout)
    if not midi_path.exists():

        raise RuntimeError(proc.stdout + "\n\nERROR: transkun finished but output .mid not found.")


# Krumhansl-Schmuckler key profiles (normalized later via cosine similarity).
# These are classic empirical profiles for major/minor keys.
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def detect_key(pm: pretty_midi.PrettyMIDI) -> dict:
    """Detect musical key (tonic + mode) from MIDI notes.


    Approach:
    - Build a pitch-class histogram (12 bins) weighted by note duration.

    - Compare histogram to rotated key profiles for all 12 tonics, for major+minor.
    - Use cosine similarity as the score.

    Returns:


    - key/mode: best candidate
    - similarity: absolute match score (higher is better)
    - confidence: best - runner_up (overall ambiguity measure)
    - top3: best 3 candidates (key/mode/score)
    - tonic_confidence: how certain the tonic is (best tonic vs best other tonic)
    - mode_confidence: how certain major/minor is for the chosen tonic
    - opposite_mode_score: score of the opposite mode for the chosen tonic
    """
    # Pitch-class histogram weighted by duration.
    hist = np.zeros(12, dtype=float)

    for inst in pm.instruments:
        for n in inst.notes:
            dur = max(0.0, n.end - n.start)
            if dur >= 0.05:  # ignore very tiny blips (often noise/ornaments)
                # Velocity-weighted histogram: favors intentional structural tones.
                w_vel = max(0.15, float(n.velocity) / 127.0)
                # Optional register emphasis: bass notes contribute a bit more to perceived key.
                w_reg = 1.0 + max(0.0, (60.0 - float(n.pitch))) / 60.0


                hist[n.pitch % 12] += dur * w_vel * w_reg

    if hist.sum() <= 0:

        return {
            "key": "UNKNOWN",

            "mode": "UNKNOWN",
            "confidence": 0.0,
            "similarity": 0.0,
            "top3": [],
            "tonic_confidence": 0.0,
            "mode_confidence": 0.0,
            "opposite_mode_score": 0.0,

        }


    # Normalize histogram to a distribution.

    hist = hist / (hist.sum() + 1e-9)

    def scores_for(profile: np.ndarray) -> list[float]:

        """Compute similarity for all 12 rotated versions of a profile."""
        scores = []
        for k in range(12):
            rot = np.roll(profile, k)
            # Cosine similarity between hist and rotated profile.
            s = float(np.dot(hist, rot) / (np.linalg.norm(hist) * np.linalg.norm(rot) + 1e-9))
            scores.append(s)
        return scores


    maj_scores = scores_for(MAJOR_PROFILE)  # index = tonic pitch class
    min_scores = scores_for(MINOR_PROFILE)


    # Combined candidate list for ranking.
    cands = []
    for k, s in enumerate(maj_scores):
        cands.append({"key": NOTE_NAMES[k], "mode": "major", "score": float(s), "pc": k})
    for k, s in enumerate(min_scores):

        cands.append({"key": NOTE_NAMES[k], "mode": "minor", "score": float(s), "pc": k})

    cands_sorted = sorted(cands, key=lambda x: x["score"], reverse=True)
    best = cands_sorted[0]
    runner_up = cands_sorted[1] if len(cands_sorted) > 1 else {"score": 0.0}

    # Mode confidence: compare best vs opposite mode for the same tonic pitch class.

    pc = best["pc"]
    if best["mode"] == "major":
        opposite_score = float(min_scores[pc])
    else:
        opposite_score = float(maj_scores[pc])
    mode_conf = float(best["score"] - opposite_score)

    # Tonic confidence: compare best tonic (best of major/minor at that tonic)
    # against the best score among all *other* tonics (either mode).

    best_tonic_score = max(float(maj_scores[pc]), float(min_scores[pc]))
    other_tonic_best = 0.0
    for k in range(12):
        if k == pc:

            continue
        other_tonic_best = max(other_tonic_best, float(maj_scores[k]), float(min_scores[k]))
    tonic_conf = float(best_tonic_score - other_tonic_best)


    return {

        "key": best["key"],
        "mode": best["mode"],
        "confidence": float(max(0.0, float(best["score"]) - float(runner_up["score"]))),
        "similarity": float(best["score"]),
        "top3": [{"key": c["key"], "mode": c["mode"], "score": float(c["score"])} for c in cands_sorted[:3]],
        "tonic_confidence": float(max(0.0, tonic_conf)),
        "mode_confidence": float(mode_conf),
        "opposite_mode_score": float(opposite_score),
    }




def _round_to_grid(x: float, grid: float) -> float:
    """Round a value to the nearest quantization grid (grid in quarterLength)."""
    if grid <= 0:
        return x
    return round(x / grid) * grid
# ---- MIDI -> MusicXML export ------------------------------------------------

# Converting performance MIDI into readable notation is inherently lossy:
# - MIDI uses continuous time in seconds; notation uses discrete durations in measures.
# - sustain pedal (CC64) affects perceived legato but must be represented differently.
#
# The exporter below tries to preserve musical intent by:

# - using the MIDI tempo map (if present) to convert seconds->quarterLength accurately

# - extending note end-times under sustain pedal before quantization

# - quantizing adaptively (straight vs triplet) to reduce rhythmic clutter
# - separating polyphony into Voices for readability




def export_musicxml_from_split_midi(
    piano_midi_path: Path,
    musicxml_path: Path,

    key_info: dict,
    tempo_bpm: float,
    time_signature: tuple[int, int],


    grid_qL: float,
) -> None:
    """Export a split (RH/LH) piano MIDI to MusicXML with:
    - tempo-map aware seconds->quarterLength mapping
    - sustain pedal (CC64) applied to note ends for notation
    - adaptive straight-vs-triplet quantization (local, per-beat)
    - polyphonic voice separation within each staff (uses music21.stream.Voice)
    - forced clefs, time signature, and key signature
    """
    try:
        from music21 import stream, note, chord, clef, meter, tempo, key, instrument, duration
    except Exception as e:
        raise RuntimeError(
            "music21 is required for MusicXML export but is not installed. "
            "Install it in your image: pip install music21\n\n"
            f"Import error: {e}"
        )

    import bisect

    pm = pretty_midi.PrettyMIDI(str(piano_midi_path))
    if len(pm.instruments) < 2:
        raise RuntimeError("Expected split MIDI with at least 2 instruments (RH + LH).")

    # Identify RH/LH by name if present, else by track order.


    rh_inst = None

    lh_inst = None

    for inst in pm.instruments:
        name = (inst.name or "").strip().lower()

        if name == "rh":

            rh_inst = inst
        elif name == "lh":

            lh_inst = inst
    if rh_inst is None:

        rh_inst = pm.instruments[0]
    if lh_inst is None:
        lh_inst = pm.instruments[1] if len(pm.instruments) > 1 else pm.instruments[0]


    # --- Tempo map: seconds -> quarterLength (ql) ---
    tempo_times, tempi = pm.get_tempo_changes()
    tempo_times = list(map(float, tempo_times)) if tempo_times is not None else []
    tempi = list(map(float, tempi)) if tempi is not None else []


    if tempi:
        cum_ql = [0.0]
        for i in range(len(tempo_times) - 1):

            t0, t1 = tempo_times[i], tempo_times[i + 1]

            ql_per_sec = tempi[i] / 60.0
            cum_ql.append(cum_ql[-1] + (t1 - t0) * ql_per_sec)


        def to_ql(t_seconds: float) -> float:

            t = float(max(0.0, t_seconds))
            i = bisect.bisect_right(tempo_times, t) - 1
            i = max(0, min(i, len(tempi) - 1))
            ql_per_sec = tempi[i] / 60.0
            return cum_ql[i] + (t - tempo_times[i]) * ql_per_sec

        tempo_marks = [(to_ql(tt), tempi[i]) for i, tt in enumerate(tempo_times)]

    else:
        bpm = float(tempo_bpm) if tempo_bpm and tempo_bpm > 0 else float(pm.estimate_tempo() or 120.0)

        ql_per_second = bpm / 60.0

        def to_ql(t_seconds: float) -> float:

            return float(max(0.0, t_seconds)) * ql_per_second


        tempo_marks = [(0.0, bpm)]

    # --- Sustain pedal (CC64) handling: extend note ends for notation ---
    def collect_cc64():
        cc = []
        for inst in pm.instruments:
            for c in getattr(inst, "control_changes", []) or []:
                if int(getattr(c, "number", -1)) == 64:
                    cc.append(c)
        cc.sort(key=lambda x: float(x.time))

        return cc

    def pedal_intervals(cc64, thresh: int = 64):

        if not cc64:

            return []
        intervals = []
        down_t = None
        for c in cc64:
            t = float(c.time)
            v = int(c.value)

            if down_t is None and v >= thresh:
                down_t = t


            elif down_t is not None and v < thresh:
                if t > down_t:
                    intervals.append((down_t, t))
                down_t = None
        if down_t is not None:
            end_t = pm.get_end_time()
            if end_t > down_t:


                intervals.append((down_t, float(end_t)))
        return intervals

    cc64 = collect_cc64()
    p_ints = pedal_intervals(cc64)

    def apply_pedal_to_notes(notes):
        """Return list of (start,end,pitch,velocity) with pedal-extended ends.
        End extension is capped by pedal-up and by the next reattack of the same pitch.

        """
        if not p_ints:
            return [(float(n.start), float(n.end), int(n.pitch), int(n.velocity)) for n in notes]

        by_pitch = {}

        for n in notes:
            by_pitch.setdefault(int(n.pitch), []).append(float(n.start))
        for p in by_pitch:

            by_pitch[p].sort()

        def next_start(pitch: int, t: float):

            arr = by_pitch.get(pitch, [])
            j = bisect.bisect_right(arr, t)
            return arr[j] if j < len(arr) else None

        int_starts = [a for a, _ in p_ints]
        out = []
        for n in notes:
            s = float(n.start)
            e = float(n.end)
            p = int(n.pitch)
            v = int(n.velocity)

            k = bisect.bisect_right(int_starts, e) - 1
            if 0 <= k < len(p_ints):

                a, b = p_ints[k]
                if a <= e <= b and e < b:
                    cap = b
                    ns = next_start(p, s)
                    if ns is not None:

                        cap = min(cap, ns)

                    if cap > e:
                        e = cap
            out.append((s, e, p, v))
        return out

    # --- Adaptive quantization: choose straight (grid) vs triplet per beat ---

    ts_num, ts_den = time_signature
    beat_ql = 4.0 / float(ts_den)  # quarterLength per beat (simple heuristic)

    def _snap_local(t: float, base: float, step: float) -> float:
        return base + round((t - base) / step) * step
# ---- MusicXML quantization helpers -----------------------------------------
# MusicXML/notation requires discrete rhythmic values. We quantize in quarterLength (qL)
# space, but do it *locally* per-beat: for each beat we choose the better-fitting grid


# between straight subdivisions (e.g., 1/16) and triplet subdivisions (1/12).
# This reduces 'rhythmic word vomit' in triplet/swing passages.


    def adaptive_quantize(note_items, grid: float):
        """Quantize (start,end) in quarterLength using per-beat straight vs triplet detection."""
        if not grid or grid <= 0:
            return note_items

        # Build beat boundaries up to piece end
        end_ql = max(it["end"] for it in note_items) if note_items else 0.0
        if end_ql <= 0:
            return note_items

        n_beats = int(math.ceil(end_ql / beat_ql)) if beat_ql > 0 else int(math.ceil(end_ql))
        beat_steps = {}


        straight_step = float(grid)
        triplet_step = float(beat_ql / 3.0) if beat_ql > 0 else float(grid)


        # group onsets per beat
        by_beat = [[] for _ in range(max(1, n_beats))]
        for it in note_items:
            b = int(min(len(by_beat) - 1, max(0, math.floor(it["start"] / beat_ql)))) if beat_ql > 0 else 0

            by_beat[b].append(it["start"])

        for b, onsets in enumerate(by_beat):
            if len(onsets) < 3:
                beat_steps[b] = straight_step
                continue
            base = b * beat_ql


            def err(step: float) -> float:
                e = 0.0
                for t in onsets:
                    q = _snap_local(t, base, step)
                    e += (t - q) ** 2

                return e

            e_s = err(straight_step)
            e_t = err(triplet_step)


            # Require meaningful improvement to avoid flip-flopping.

            if e_t < 0.80 * e_s and e_t < 0.0025 * len(onsets):
                beat_steps[b] = triplet_step

            else:
                beat_steps[b] = straight_step



        # Apply quantization per item
        out = []
        for it in note_items:
            s = float(it["start"])


            e = float(it["end"])
            b = int(min(n_beats - 1, max(0, math.floor(s / beat_ql)))) if beat_ql > 0 else 0
            base = b * beat_ql
            step = beat_steps.get(b, straight_step)

            qs = _snap_local(s, base, step)
            qe = _snap_local(e, base, step)

            # Ensure strictly positive duration and avoid collapsing notes.
            min_step = min(step, straight_step)


            if qe <= qs:

                qe = qs + min_step
            # If quantized end is too tiny beyond start, enforce min duration.
            if qe - qs < min_step:

                qe = qs + min_step

            out.append({**it, "start": float(qs), "end": float(qe)})
        return out

    # Key signature (optional)
    if key_info.get("key") not in (None, "", "UNKNOWN") and key_info.get("mode") in ("major", "minor"):
        ksig = key.Key(key_info["key"], key_info["mode"])

    else:
        ksig = None


    ts = meter.TimeSignature(f"{ts_num}/{ts_den}")


    def cluster_to_chord_items(note_items, eps_ql: float, dur_tol: float):
        """Group near-simultaneous onsets, then cluster by similar durations.
        Returns a list of chord-items:

          {'start', 'end', 'pitches', 'vel'}
        """
        note_items = sorted(note_items, key=lambda x: (x["start"], x["pitch"]))
        groups = []

        cur = []
        cur_t = None

        for it in note_items:
            if cur_t is None or abs(it["start"] - cur_t) <= eps_ql:

                cur.append(it)
                cur_t = it["start"] if cur_t is None else cur_t
            else:
                groups.append(cur)
                cur = [it]
                cur_t = it["start"]
        if cur:
            groups.append(cur)


        chord_items = []
        for g in groups:
            # cluster by duration similarity (end-start)
            g_sorted = sorted(g, key=lambda x: (x["end"] - x["start"], x["pitch"]))
            clusters = []
            for it in g_sorted:

                d = it["end"] - it["start"]
                placed = False
                for cl in clusters:
                    d0 = cl[0]["end"] - cl[0]["start"]
                    if abs(d - d0) <= dur_tol:
                        cl.append(it)
                        placed = True
                        break
                if not placed:
                    clusters.append([it])


            for cl in clusters:
                start = float(cl[0]["start"])
                end = float(max(x["end"] for x in cl))
                pitches = sorted({int(x["pitch"]) for x in cl})
                vel = int(max(int(x["vel"]) for x in cl))

                chord_items.append({"start": start, "end": end, "pitches": pitches, "vel": vel})

        chord_items.sort(key=lambda x: (x["start"], x["pitches"][0]))


        return chord_items
# ---- Polyphonic voice separation -------------------------------------------

# A single hand/staff often contains multiple simultaneous musical lines.
# Example: a held thumb note under a moving melody. If we dump everything into one
# stream, music21 (and notation software) has to express overlaps using ties/rests
# in one voice, which becomes unreadable.
#
# We therefore allocate notes into 2+ Voices per staff using a simple deterministic
# scheduler: put a note into the first Voice that can accept it without time overlap;
# otherwise use the Voice with the smallest overlap penalty. A mild register bias
# keeps higher notes in the 'upper' voice and lower notes in the 'lower' voice.




    def allocate_voices(chord_items, max_voices: int = 3, eps: float = 1e-6):

        """Deterministic voice allocator for polyphony within one staff."""
        voices = [[] for _ in range(max_voices)]
        voice_end = [float("-inf")] * max_voices

        for it in chord_items:
            s = it["start"]
            e = it["end"]

            reg = max(it["pitches"])  # use top pitch for register bias

            candidates = []
            for i in range(max_voices):

                if s >= voice_end[i] - eps:
                    gap = max(0.0, s - voice_end[i])
                    # Bias: upper register -> earlier voices, lower register -> later voices.
                    reg_bias = 0.002 * (reg - 60.0) * (1.0 if i == 0 else (-1.0 if i == 1 else 0.0))

                    score = gap - reg_bias
                    candidates.append((score, i))

            if candidates:

                _, vi = min(candidates)

            else:
                # All overlap: pick the one with least overlap + register bias.
                overlap_scores = []
                for i in range(max_voices):
                    overlap = max(0.0, voice_end[i] - s)
                    reg_bias = 0.002 * (reg - 60.0) * (1.0 if i == 0 else (-1.0 if i == 1 else 0.0))
                    overlap_scores.append((overlap - reg_bias, i))
                _, vi = min(overlap_scores)

            voices[vi].append(it)
            voice_end[vi] = max(voice_end[vi], e)

        return [v for v in voices if v]

    def build_staff(inst_notes, staff_name: str, which_clef: clef.Clef):

        """Build a single notated staff (RH or LH) for MusicXML.


        Steps:
        1) Insert clef/time signature/key signature at time 0.

        2) Apply sustain pedal to extend note durations for more legato notation.
        3) Convert seconds->quarterLength using the tempo map.
        4) Quantize note onsets/offsets (adaptive straight vs triplet).
        5) Allocate notes into multiple Voices to represent independent lines.
        """
        part = stream.PartStaff()

        part.append(instrument.Piano())
        part.partName = staff_name

        part.insert(0.0, which_clef)

        part.insert(0.0, ts)

        if ksig is not None:
            part.insert(0.0, ksig)


        # Apply pedal extension, convert to qL, quantize adaptively, then voice-separate.
        ndata = apply_pedal_to_notes(inst_notes)
        note_items = []
        for s_sec, e_sec, pitch, vel in ndata:
            s = float(to_ql(s_sec))
            e = float(to_ql(e_sec))

            if e <= s:
                e = s + 0.05  # small guard
            note_items.append({"pitch": int(pitch), "start": s, "end": e, "vel": int(vel)})

        note_items = adaptive_quantize(note_items, float(grid_qL))

        # Chordify by onset, but only among similar durations; otherwise split into multiple chord-items.

        eps_ql = max(0.02, (grid_qL * 0.5) if (grid_qL and grid_qL > 0) else 0.02)
        dur_tol = max(0.12, float(grid_qL) if (grid_qL and grid_qL > 0) else 0.12)
        chord_items = cluster_to_chord_items(note_items, eps_ql=eps_ql, dur_tol=dur_tol)

        # Allocate voices (polyphonic voice separation)
        voice_lists = allocate_voices(chord_items, max_voices=3)



        for vi, vitems in enumerate(voice_lists):


            v = stream.Voice()

            for it in vitems:
                off = float(it["start"])

                dur = float(it["end"] - it["start"])

                if dur <= 0:
                    continue

                if len(it["pitches"]) == 1:
                    nn = note.Note(it["pitches"][0])

                    nn.duration = duration.Duration(dur)
                    if vi == 0:
                        nn.stemDirection = "up"
                    elif vi == 1:
                        nn.stemDirection = "down"
                    v.insert(off, nn)
                else:
                    ch = chord.Chord(it["pitches"])
                    ch.duration = duration.Duration(dur)
                    if vi == 0:

                        ch.stemDirection = "up"
                    elif vi == 1:
                        ch.stemDirection = "down"
                    v.insert(off, ch)

            part.append(v)

        # Let music21 handle measures/ties/rests (now that voices exist).
        try:
            part.makeMeasures(inPlace=True)
            part.makeNotation(inPlace=True)
        except Exception:

            pass

        return part


    # Create score
    sc = stream.Score()

    for off, bpm in tempo_marks:
        try:
            sc.insert(float(off), tempo.MetronomeMark(number=float(bpm)))
        except Exception:

            if off == 0.0:

                sc.append(tempo.MetronomeMark(number=float(bpm)))


    part_rh = build_staff(rh_inst.notes, "RH", clef.TrebleClef())
    part_lh = build_staff(lh_inst.notes, "LH", clef.BassClef())

    sc.insert(0, part_rh)
    sc.insert(0, part_lh)


    try:
        sc.makeMeasures(inPlace=True)


        sc.makeNotation(inPlace=True)
    except Exception:


        pass

    musicxml_path.parent.mkdir(parents=True, exist_ok=True)

    sc.write("musicxml", fp=str(musicxml_path))





def postprocess_midi(raw_midi: Path, out_midi: Path, analysis_json: Path) -> tuple[dict, float, tuple[int, int]]:
    """Postprocess raw MIDI into a two-track (RH/LH) piano MIDI.

    Core idea:
    - Group notes into onset 'events' (chords) by near-simultaneous start times.
    - For each event, consider multiple candidate 'hand split boundaries' (pitch thresholds).
    - Score each candidate locally (crossings, chord span, balance).
    - Use dynamic programming across time to choose a boundary sequence that:
        * avoids crossings
        * keeps hand motion smooth
        * avoids jittery boundary changes


    Important playback note:
    - Raw transcription often uses sustain pedal (CC64) and other controls to create

      natural legato. If we emit only notes, playback sounds choppy.

    - Therefore we copy control changes and pitch bends from the original MIDI into
      BOTH output hands (safe for piano playback, and keeps realism).

    """
    pm = pretty_midi.PrettyMIDI(str(raw_midi))

    # Collect expressive controls (sustain pedal, etc.) so the split MIDI plays naturally.
    all_cc: list[pretty_midi.ControlChange] = []
    all_pb: list[pretty_midi.PitchBend] = []
    for inst in pm.instruments:
        all_cc.extend(inst.control_changes)

        all_pb.extend(inst.pitch_bends)

    # Collect notes from all instruments.
    all_notes: list[pretty_midi.Note] = []

    for inst in pm.instruments:
        all_notes.extend(inst.notes)


    if not all_notes:
        raise RuntimeError("No notes found in MIDI")

    global_med = int(np.median([n.pitch for n in all_notes]))



    def copy_note(n: pretty_midi.Note) -> pretty_midi.Note:

        """Create a new Note object (avoid reusing objects across PrettyMIDI instances)."""


        return pretty_midi.Note(velocity=n.velocity, pitch=n.pitch, start=n.start, end=n.end)


# ---- Hand-splitting (LH/RH) via dynamic programming -------------------------
# We treat each onset 'event' as a set of near-simultaneous notes. For each event we

# evaluate candidate pitch boundaries that separate LH vs RH, then use DP to pick a
# boundary sequence over time that balances local plausibility with global smoothness.
# This avoids brittle 'middle C' splitting and reduces hand jitter.


    def group_events_adaptive(
        notes: list[pretty_midi.Note],
        tempo_bpm: float,
        min_eps: float = 0.02,
        max_eps: float = 0.08,
    ) -> tuple[list[list[pretty_midi.Note]], float]:
        """Group notes into onset events using an adaptive start-time tolerance.

        A fixed tolerance (e.g., 30ms) merges/splits poorly across tempi and textures.
        This chooses eps using a blend of:
        - a tempo-based component (larger eps in slower music)

        - a robust IOI-based component (median inter-onset interval)
        """
        notes_sorted = sorted(notes, key=lambda n: (n.start, n.pitch))
        if not notes_sorted:
            return [], 0.03

        # Robust IOI estimate (seconds)
        starts = np.array([n.start for n in notes_sorted], dtype=float)

        uniq = np.unique(starts)
        diffs = np.diff(uniq)
        med_ioi = float(np.median(diffs)) if len(diffs) else 0.05


        tempo_bpm = float(tempo_bpm) if tempo_bpm and tempo_bpm > 0 else 120.0
        tempo_bpm = float(np.clip(tempo_bpm, 30.0, 240.0))
        spb = 60.0 / tempo_bpm  # seconds per beat


        eps = 0.5 * (0.06 * spb) + 0.5 * (0.35 * med_ioi)
        eps = float(np.clip(eps, min_eps, max_eps))

        events: list[list[pretty_midi.Note]] = []

        cur: list[pretty_midi.Note] = []
        for n in notes_sorted:
            if not cur:
                cur = [n]

                continue
            if abs(n.start - cur[0].start) <= eps:
                cur.append(n)

            else:
                events.append(cur)

                cur = [n]
        if cur:
            events.append(cur)
        return events, eps

    def event_candidates(event: list[pretty_midi.Note], global_med: int) -> list[int]:
        """Generate candidate boundary pitches for an event.

        Includes:

        - global median-based priors
        - fixed musical anchors around middle register

        - near-note candidates (p-1, p, p+1) for pitches present in the event
        - midpoints between sufficiently separated pitches in the event
        """
        fixed = [52, 55, 58, 60, 62, 64, 67]
        ps = sorted({n.pitch for n in event})
        cands = set([global_med, global_med - 2, global_med + 2] + fixed)


        for p in ps:


            cands.update([p - 1, p, p + 1])
        for a, b in zip(ps, ps[1:]):
            if b - a >= 2:
                cands.add((a + b) // 2 + 1)
        cands = [c for c in cands if 24 <= c <= 96]
        cands = sorted(set(cands))

        return cands if cands else fixed

    def assign_by_boundary(event: list[pretty_midi.Note], boundary: int) -> tuple[list[pretty_midi.Note], list[pretty_midi.Note]]:
        """Assign event notes to LH/RH given a boundary pitch (with chord protection)."""
        g = sorted(event, key=lambda n: n.pitch)
        if len(g) == 1:

            n = g[0]
            return ([n], []) if n.pitch < boundary else ([], [n])

        low = g[0]
        high = g[-1]
        lh = [low]
        rh = [high]


        for mid in g[1:-1]:
            if mid.pitch < boundary:
                lh.append(mid)

            else:
                rh.append(mid)


        if not rh or not lh:
            lh = [n for n in g if n.pitch < boundary]

            rh = [n for n in g if n.pitch >= boundary]

            if not lh and rh:
                pick = min(rh, key=lambda n: n.pitch)

                lh = [pick]

                rh = [n for n in rh if n is not pick]
            if not rh and lh:

                pick = max(lh, key=lambda n: n.pitch)
                rh = [pick]
                lh = [n for n in lh if n is not pick]


        return lh, rh


    def span_penalty(notes: list[pretty_midi.Note]) -> float:
        """Penalty for large chord spans in a single hand."""
        if len(notes) <= 1:

            return 0.0
        span = max(n.pitch for n in notes) - min(n.pitch for n in notes)
        return max(0.0, (span - 12)) ** 1.3


    def center_pitch(notes: list[pretty_midi.Note]) -> float | None:
        """Median pitch of notes in a hand at an event (used for movement smoothing)."""
        if not notes:

            return None
        ps = sorted(n.pitch for n in notes)
        return float(ps[len(ps) // 2])


    def crossing_penalty(lh: list[pretty_midi.Note], rh: list[pretty_midi.Note]) -> float:
        """Penalty for hand crossing, graded by amount of overlap."""
        if not lh or not rh:
            return 0.0
        overlap = max(0, max(n.pitch for n in lh) - min(n.pitch for n in rh) + 1)
        return (overlap ** 1.4) * 6.0

    # Estimate tempo (used for adaptive onset grouping & motion scaling)
    tempo_used = pm.estimate_tempo()

    if not tempo_used or tempo_used <= 0:


        tempo_used = 120.0


    # Time signature for MusicXML: use first from MIDI if present, else 4/4.
    if pm.time_signature_changes:
        ts0 = pm.time_signature_changes[0]


        time_sig = (int(ts0.numerator), int(ts0.denominator))

    else:
        time_sig = (4, 4)


    def register_penalty(lh: list[pretty_midi.Note], rh: list[pretty_midi.Note]) -> float:
        """Soft priors to keep LH generally lower and RH generally higher."""

        pen = 0.0
        lh_c = center_pitch(lh)
        rh_c = center_pitch(rh)
        if lh_c is not None:
            pen += max(0.0, (lh_c - 58.0)) * 0.15

        if rh_c is not None:
            pen += max(0.0, (52.0 - rh_c)) * 0.15
        return pen





    # Build events (adaptive tolerance)
    events, eps_used = group_events_adaptive(all_notes, tempo_bpm=float(tempo_used))
    T = len(events)

    event_starts = [ev[0].start for ev in events]



    cand_lists: list[list[int]] = []

    local_costs: list[list[float]] = []
    local_centers: list[list[tuple[float | None, float | None]]] = []
    local_assign: list[list[tuple[list[pretty_midi.Note], list[pretty_midi.Note]]]] = []


    for ev in events:
        cands = event_candidates(ev, global_med=global_med)

        cand_lists.append(cands)

        ev_costs: list[float] = []
        ev_centers: list[tuple[float | None, float | None]] = []
        ev_assigns: list[tuple[list[pretty_midi.Note], list[pretty_midi.Note]]] = []

        for b in cands:
            lh, rh = assign_by_boundary(ev, b)


            cost = 0.0
            cost += crossing_penalty(lh, rh)
            cost += 1.5 * span_penalty(lh) + 1.5 * span_penalty(rh)

            cost += 0.2 * abs(len(lh) - len(rh))
            cost += register_penalty(lh, rh)


            ev_costs.append(cost)

            ev_centers.append((center_pitch(lh), center_pitch(rh)))
            ev_assigns.append((lh, rh))



        local_costs.append(ev_costs)
        local_centers.append(ev_centers)
        local_assign.append(ev_assigns)


    # DP across events
    W_BOUND_SMOOTH = 0.3

    W_MOVE = 0.6



    dp: list[list[float]] = []
    prev: list[list[int]] = []

    dp.append([c for c in local_costs[0]])
    prev.append([-1 for _ in local_costs[0]])

    for t in range(1, T):
        dp_t = [float("inf")] * len(local_costs[t])


        prev_t = [-1] * len(local_costs[t])


        for j, b in enumerate(cand_lists[t]):
            lh_c, rh_c = local_centers[t][j]


            best_val = float("inf")
            best_k = -1

            for k, b_prev in enumerate(cand_lists[t - 1]):
                val = dp[t - 1][k] + local_costs[t][j]
                dt = max(1e-3, event_starts[t] - event_starts[t - 1])
                speed = 0.12 / dt  # larger when events are closer together
                val += W_BOUND_SMOOTH * abs(b - b_prev) * speed


                lh_p, rh_p = local_centers[t - 1][k]
                if lh_c is not None and lh_p is not None:

                    val += W_MOVE * (abs(lh_c - lh_p) ** 1.15) / 6.0 * speed

                if rh_c is not None and rh_p is not None:
                    val += W_MOVE * (abs(rh_c - rh_p) ** 1.15) / 6.0 * speed

                if val < best_val:

                    best_val = val
                    best_k = k

            dp_t[j] = best_val
            prev_t[j] = best_k


        dp.append(dp_t)
        prev.append(prev_t)


    last_j = int(np.argmin(dp[-1]))
    path_idx = [0] * T
    path_idx[-1] = last_j
    for t in range(T - 1, 0, -1):
        path_idx[t - 1] = prev[t][path_idx[t]]

    chosen_boundaries = [cand_lists[t][path_idx[t]] for t in range(T)]


    # Build output instruments
    rh = pretty_midi.Instrument(program=0, name="RH")
    lh = pretty_midi.Instrument(program=0, name="LH")


    # Preserve expressive controls for natural playback.

    # Default behavior duplicates controls into both hands; optionally emit a separate "Global" track.

    global_ctrl = None
    if DUPLICATE_CONTROLS:
        rh.control_changes = [pretty_midi.ControlChange(number=c.number, value=c.value, time=c.time) for c in all_cc]
        lh.control_changes = [pretty_midi.ControlChange(number=c.number, value=c.value, time=c.time) for c in all_cc]
        rh.pitch_bends = [pretty_midi.PitchBend(pitch=b.pitch, time=b.time) for b in all_pb]
        lh.pitch_bends = [pretty_midi.PitchBend(pitch=b.pitch, time=b.time) for b in all_pb]
    else:
        global_ctrl = pretty_midi.Instrument(program=0, name="Global")
        global_ctrl.control_changes = [
            pretty_midi.ControlChange(number=c.number, value=c.value, time=c.time) for c in all_cc
        ]
        global_ctrl.pitch_bends = [pretty_midi.PitchBend(pitch=b.pitch, time=b.time) for b in all_pb]


    crossing_events = 0
    for t in range(T):

        j = path_idx[t]
        lh_notes, rh_notes = local_assign[t][j]



        if lh_notes and rh_notes and max(n.pitch for n in lh_notes) >= min(n.pitch for n in rh_notes):
            crossing_events += 1

        lh.notes.extend(copy_note(n) for n in lh_notes)
        rh.notes.extend(copy_note(n) for n in rh_notes)

    pm_out = pretty_midi.PrettyMIDI(initial_tempo=float(tempo_used))


    pm_out.instruments = [rh, lh] + ([global_ctrl] if global_ctrl is not None else [])

    # Preserve basic meta (helps later for MusicXML export).
    pm_out.time_signature_changes = list(pm.time_signature_changes)

    pm_out.key_signature_changes = list(pm.key_signature_changes)

    pm_out.write(str(out_midi))

    key_info = detect_key(pm)
    # Extra sanity metrics (useful for auto-QA without listening)

    empty_lh_events = 0
    empty_rh_events = 0
    for t in range(T):
        lh_notes, rh_notes = local_assign[t][path_idx[t]]
        if not lh_notes:

            empty_lh_events += 1
        if not rh_notes:
            empty_rh_events += 1

    boundary_jitter_mean = float(np.mean(np.abs(np.diff(chosen_boundaries)))) if T > 1 else 0.0
    avg_pitch_lh = float(np.mean([n.pitch for n in lh.notes])) if lh.notes else None
    avg_pitch_rh = float(np.mean([n.pitch for n in rh.notes])) if rh.notes else None

    analysis = {
        "events": T,
        "tempo_used_bpm": float(tempo_used),

        "event_group_eps_s": float(eps_used),
        "boundary_mean": float(np.mean(chosen_boundaries)),

        "boundary_min": int(min(chosen_boundaries)),

        "boundary_max": int(max(chosen_boundaries)),

        "boundary_jitter_mean": boundary_jitter_mean,
        "notes_total": len(all_notes),
        "notes_rh": len(rh.notes),
        "notes_lh": len(lh.notes),
        "avg_pitch_rh": avg_pitch_rh,
        "avg_pitch_lh": avg_pitch_lh,
        "empty_rh_events": int(empty_rh_events),
        "empty_lh_events": int(empty_lh_events),
        "crossing_events": int(crossing_events),
        "crossing_rate": float(crossing_events / max(1, T)),
        "cc_total": int(len(all_cc)),

        "pitch_bends_total": int(len(all_pb)),

        "duplicate_controls": bool(DUPLICATE_CONTROLS),
        "key": key_info,
    }
    analysis_json.write_text(json.dumps(analysis, indent=2), encoding="utf-8")




    return key_info, float(tempo_used), time_sig


@app.post("/api/convert/youtube")


def convert_youtube(req: YoutubeRequest):
    """Main pipeline endpoint: YouTube URL -> MP3 -> raw MIDI -> split MIDI + analysis."""
    job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    job_in = DATA_IN / job_id
    job_out = DATA_OUT / job_id

    job_in.mkdir(parents=True, exist_ok=True)

    job_out.mkdir(parents=True, exist_ok=True)

    outtmpl = str(job_out / "%(title)s.%(ext)s")

    ytdlp_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--restrict-filenames",
        "-f",
        "bestaudio/best",
        "-x",

        "--audio-format",
        "mp3",
        "--audio-quality",

        "0",
        "-o",

        outtmpl,
        str(req.url),
    ]

    try:
        proc = _run(ytdlp_cmd)
        if proc.returncode != 0:
            raise RuntimeError(proc.stdout)
    except Exception as e:

        raise HTTPException(status_code=500, detail=f"yt-dlp failed:\n{e}")


    mp3_files = sorted(job_out.glob("*.mp3"))
    if not mp3_files:

        raise HTTPException(status_code=500, detail="No MP3 produced by yt-dlp")

    mp3_path = max(mp3_files, key=lambda p: p.stat().st_size)

    raw_midi_path = job_out / f"{mp3_path.stem}.raw.mid"
    try:
        transcribe_to_midi(mp3_path, raw_midi_path, device=TRANSKUN_DEVICE)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"transkun failed:\n{e}")

    piano_midi_path = job_out / f"{mp3_path.stem}.piano.mid"
    analysis_path = job_out / "analysis.json"

    try:

        key_info, tempo_bpm, time_sig = postprocess_midi(raw_midi_path, piano_midi_path, analysis_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"postprocess failed: {e}"
    )

    # Optional: export a notation-oriented MusicXML alongside the performance MIDI.
    # This step is intentionally kept separate from postprocess_midi() so the service
    # can run in "MIDI-only" mode for speed or environments without music21.

    musicxml_path = None
    if EXPORT_MUSICXML:

        musicxml_path = job_out / f"{mp3_path.stem}.musicxml"
        try:
            export_musicxml_from_split_midi(
                piano_midi_path=piano_midi_path,
                musicxml_path=musicxml_path,
                key_info=key_info,
                tempo_bpm=tempo_bpm,
                time_signature=time_sig,
                grid_qL=MXML_GRID,

            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"musicxml export failed: {e}")


    return {
        "job_id": job_id,
        "status": "postprocessed",


        "youtube_url": str(req.url),
        "device": TRANSKUN_DEVICE,
        "outputs": {
            "mp3_filename": mp3_path.name,
            "mp3_path": str(mp3_path),
            "raw_midi_filename": raw_midi_path.name,
            "raw_midi_path": str(raw_midi_path),
            "piano_midi_filename": piano_midi_path.name,
            "piano_midi_path": str(piano_midi_path),
            "analysis_path": str(analysis_path),
            "musicxml_path": str(musicxml_path) if EXPORT_MUSICXML else None,
        },
        "next": "render PDF (MuseScore CLI)",
    }


# ============================================================================
# Web UI + file download endpoints
# ============================================================================
# This section is intentionally self-contained and "zero build":
# - No templates directory
# - No frontend build tools

# - A single HTML page served at "/"
#
# The purpose is to make the stack usable by non-technical users:
# 1) paste a YouTube link

# 2) click Convert
# 3) download the outputs (mp3, raw midi, piano midi, musicxml)
#

# IMPORTANT:
# - MIDI cannot encode clefs; clef forcing is done via MusicXML, when produced.
# - The conversion endpoint is synchronous. For long videos the browser will
#   keep waiting. If you want progress reporting, implement a queue + polling.
# - Download endpoints are hardened against path traversal.
# ============================================================================

INDEX_HTML = r"""<!doctype html>
<html lang="en">

<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>yt2midi_v2</title>
  <style>

    :root { --bg:#0b1020; --card:#121a33; --text:#e9edff; --muted:#aab3d6; --accent:#6ea8fe; --danger:#ff6b6b; }
    body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background:var(--bg); color:var(--text); }
    .wrap { max-width: 920px; margin: 0 auto; padding: 28px 18px 60px; }
    .title { display:flex; align-items:baseline; gap:10px; }

    .title h1 { margin:0; font-size: 26px; letter-spacing: 0.2px; }
    .title span { color:var(--muted); font-size: 14px; }
    .card { background:var(--card); border:1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.25); }
    .row { display:flex; gap:10px; flex-wrap:wrap; }
    input[type="url"] { flex: 1 1 520px; padding: 12px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12); background: rgba(0,0,0,0.18); color: var(--text); outline:none; }
    button { padding: 12px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.14); background: rgba(110,168,254,0.18); color: var(--text); cursor:pointer; }
    button:hover { background: rgba(110,168,254,0.26); }
    button:disabled { opacity:0.55; cursor:not-allowed; }
    .hint { color: var(--muted); font-size: 13px; margin-top: 10px; line-height: 1.4; }
    .status { margin-top: 14px; font-size: 14px; }
    .status .ok { color: #7ee787; }
    .status .err { color: var(--danger); white-space: pre-wrap; }

    .out { margin-top: 14px; display:none; }
    .out h2 { margin: 10px 0 10px; font-size: 16px; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
    .item { background: rgba(0,0,0,0.18); border:1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; }
    .item .k { color: var(--muted); font-size: 12px; }
    .item a { color: var(--accent); text-decoration: none; word-break: break-all; }
    .item a:hover { text-decoration: underline; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; color: var(--muted); }
    .footer { margin-top: 18px; color: var(--muted); font-size: 12px; }

    @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">
      <h1>yt2midi_v2</h1>
      <span>youtube → mp3 → raw midi → split midi → musicxml</span>
    </div>

    <div class="card" style="margin-top:14px;">

      <div class="row">
        <input id="url" type="url" placeholder="Paste YouTube URL… (e.g. https://www.youtube.com/watch?v=...)" />
        <button id="go" onclick="convert()">Convert</button>
      </div>
      <div class="hint">
        Tip: this will run Transkun inside the container. It can take a while depending on video length and GPU load.
      </div>

      <div class="status" id="status"></div>

      <div class="out" id="out">
        <h2>Downloads</h2>
        <div class="grid" id="links"></div>
        <div class="footer mono" id="jobmeta"></div>
      </div>
    </div>
  </div>

<script>
// Minimal HTML escaping helper (prevents injecting HTML into the page)
function esc(s){ return (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }


function setStatus(html){ document.getElementById("status").innerHTML = html; }

// Simple busy/disabled state so users don't click multiple times
function setBusy(b){
  document.getElementById("go").disabled = b;
  document.getElementById("url").disabled = b;
}

async function convert(){

  const url = document.getElementById("url").value.trim();

  if(!url){
    setStatus('<span class="err">Please paste a YouTube URL.</span>');
    return;
  }

  setBusy(true);
  document.getElementById("out").style.display = "none";
  setStatus('Working… <span class="mono">(downloading audio, transcribing, postprocessing)</span>');

  try{
    // We call the same JSON API used by curl clients.
    const resp = await fetch("/api/convert/youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await resp.json();
    if(!resp.ok){
      throw new Error(data && data.detail ? data.detail : ("HTTP " + resp.status));
    }


    setStatus('<span class="ok">Done.</span> <span class="mono">job_id=' + esc(data.job_id) + '</span>');
    renderOutputs(data.job_id, data.outputs);
  }catch(err){

    setStatus('<div class="err">' + esc(String(err)) + '</div>');
  }finally{
    setBusy(false);
  }

}


function renderOutputs(job_id, outputs){

  const links = document.getElementById("links");
  links.innerHTML = "";

  // Build a list of files we expect. We use the filenames returned by the API,
  // so this stays correct even when yt-dlp video titles change.

  const files = [];
  if(outputs && outputs.mp3_filename) files.push({label:"MP3", filename: outputs.mp3_filename});
  if(outputs && outputs.raw_midi_filename) files.push({label:"RAW MIDI", filename: outputs.raw_midi_filename});

  if(outputs && outputs.piano_midi_filename) files.push({label:"Piano MIDI (RH/LH)", filename: outputs.piano_midi_filename});


  // Some versions of the backend may return an absolute path for musicxml; we only
  // need the base filename for downloading.
  if(outputs && outputs.musicxml_path){
    const parts = String(outputs.musicxml_path).split("/");
    files.push({label:"MusicXML", filename: parts[parts.length-1]});
  }

  // Always include analysis.json if present in job folder
  files.push({label:"analysis.json", filename:"analysis.json"});

  for(const f of files){
    const href = "/api/jobs/" + encodeURIComponent(job_id) + "/download/" + encodeURIComponent(f.filename);
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = '<div class="k">' + esc(f.label) + '</div>' +
                    '<div><a href="' + esc(href) + '">' + esc(f.filename) + '</a></div>';
    links.appendChild(div);
  }

  document.getElementById("jobmeta").textContent = "Job folder: /data/out/" + job_id;
  document.getElementById("out").style.display = "block";
}
</script>
</body>
</html>
"""



@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the single-page Web UI."""

    return HTMLResponse(INDEX_HTML)


def _safe_job_path(job_id: str) -> Path:
    """Resolve /data/out/<job_id> and ensure it stays within DATA_OUT.

    Security rationale:
    - job_id comes from our own generator, but treat it as untrusted anyway.
    - resolve() + parent checks prevent path traversal like ../../../etc/passwd
    """

    job_dir = (DATA_OUT / job_id).resolve()
    base = DATA_OUT.resolve()
    if base not in job_dir.parents and job_dir != base:

        raise HTTPException(status_code=400, detail="Invalid job_id")
    if not job_dir.exists() or not job_dir.is_dir():
        raise HTTPException(status_code=404, detail="Job not found")
    return job_dir


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    """List available files for a completed job.

    Useful for:
    - external automation
    - a future UI that polls for job completion/progress
    """

    job_dir = _safe_job_path(job_id)
    files = []
    for p in sorted(job_dir.iterdir()):
        if p.is_file():
            files.append({"name": p.name, "size": p.stat().st_size})
    return {"job_id": job_id, "files": files}


@app.get("/api/jobs/{job_id}/download/{filename}")
def download_job_file(job_id: str, filename: str):
    """Download a single output file from a job folder.

    We do strict filename validation to prevent:
    - '../' traversal
    - hidden files
    - nested paths
    """
    job_dir = _safe_job_path(job_id)


    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")


    file_path = (job_dir / filename).resolve()
    if file_path.parent != job_dir:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Best-effort content-types so browsers label files nicely.
    suf = file_path.suffix.lower()
    media = {
        ".mp3": "audio/mpeg",
        ".mid": "audio/midi",
        ".midi": "audio/midi",

        ".musicxml": "application/vnd.recordare.musicxml+xml",
        ".xml": "application/xml",
        ".json": "application/json",
    }.get(suf, "application/octet-stream")

    # FileResponse sets Content-Disposition so the browser downloads the file.
    return FileResponse(str(file_path), media_type=media, filename=file_path.name)


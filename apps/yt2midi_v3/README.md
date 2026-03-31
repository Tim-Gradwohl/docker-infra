# yt2midi_v3

## Purpose

yt2midi_v3 provides a **YouTube → MIDI pipeline**:

* download audio from YouTube
* transcribe audio to MIDI using GPU (Transkun)
* expose a web interface for user interaction

---

## Architecture

Two-container design:

* `ui` → nginx static frontend
* `api` → backend (CUDA + transcription)

Flow:

User
→ UI (nginx)
→ API
→ yt-dlp download
→ Transkun processing (GPU)
→ output files

---

## Containers

* `yt2midi_v3_ui`
* `yt2midi_v3_api`

---

## GPU

Enabled via Docker Compose:

```text id="q4r2ab"
gpus: all
```

Base image:

```text id="8h6n4c"
nvidia/cuda:11.8.0-runtime-ubuntu22.04
```

Notes:

* requires working NVIDIA setup in Docker
* designed for Pascal (GTX 1060 compatible)

---

## Networking

Networks:

* `internal` → UI ↔ API communication
* `proxy` → Traefik routing

---

## Routing

Defined via Traefik labels.

Parameterized:

```text id="0q7vwe"
${APP_ID}
${APP_HOST}
```

Example:

```text id="0ppr4v"
Host(${APP_HOST})
```

Access:

* LAN: http://${APP_HOST}
* WAN (if enabled): https://${APP_HOST}

---

## Configuration

### Stack name

```text id="v2e7uy"
name: ${APP_ID}
```

→ allows reuse across environments

---

### Timezone

```text id="b5gkdi"
TZ=${TZ:-Europe/Berlin}
```

---

### Traefik

```text id="y7a0o3"
${TRAEFIK_CERTRESOLVER:-cloudflare}
```

---

## Storage

Bind mounts:

```text id="h7x0yq"
/mnt/d/Docker/yt2midi_v3/data/in
/mnt/d/Docker/yt2midi_v3/data/out
```

Mapped to:

* `/data/in`
* `/data/out`

Purpose:

* input files
* generated MIDI/audio outputs

---

## Operations

### Deploy / update

```bash id="e1e8f2"
stack up yt2midi_v3
```

### Logs

```bash id="d7a3b1"
stack logs yt2midi_v3
```

---

## Exposure Model

* no direct port exposure
* all traffic via Traefik
* optional WAN via Cloudflare Tunnel

---

## Workflow

1. User submits YouTube URL
2. yt-dlp downloads audio
3. Transkun processes audio (GPU)
4. MIDI output generated
5. files available for download

---

## Debugging

### Service not reachable

Check:

* containers running
* attached to `proxy` network
* Traefik labels correct

---

### GPU not working

Check:

* `docker info | grep -i nvidia`
* container has GPU access
* correct CUDA image

---

### Processing fails

Check:

* logs from API container
* input/output directories writable
* disk space available

---

## Failure Modes

### Slow or failed transcription

Cause:

* GPU not available → CPU fallback
* incorrect CUDA setup

---

### Files not generated

Cause:

* permission issue in bind mounts
* failed yt-dlp download

---

## Notes

* compute-heavy workload
* depends on GPU availability for performance
* parameterized for portability across stacks

---

## References

* Gateway → `gateway/README.md`
* Ingress → `docs/architecture/ingress-cloudflare-traefik.md`
* System context → `ai-context.md`


# yt2midi (minimal UI + Docker)

This repo serves a static web UI (Nginx) and a FastAPI backend that downloads YouTube audio (yt-dlp),
extracts MP3, and generates MIDI via Transkun.

## Run (local)

```bash
docker compose up --build
```

Open: http://localhost:8080

Output files land in `/mnt/d/Docker/yt2midi_v3/data/out/<job-id>/`.

## Notes

- For GPU support you need NVIDIA Container Toolkit; then uncomment the GPU section in `compose.yaml`.
- The UI polls job status and shows a progress bar to avoid "is it stuck?" confusion.

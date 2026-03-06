# yt2midi (minimal UI + Docker)

This repo serves a static web UI (Nginx) and a FastAPI backend that downloads YouTube audio (yt-dlp),
extracts MP3, and generates MIDI via Transkun.

## Run (local)

```bash
docker compose up --build
```

Open: http://localhost:8080

Output files land in `./data/out/<job-id>/`.

## Notes

- For GPU support you need NVIDIA Container Toolkit; then uncomment the GPU section in `compose.yaml`.
- The UI polls job status and shows a progress bar to avoid "is it stuck?" confusion.

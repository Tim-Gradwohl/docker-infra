# Paperless

## Purpose

Document management stack based on Paperless-ngx, with the local AI companions from the Techno Tim guide adapted to this repo's Traefik-first model.

Provides:

* `paperless` for ingestion, OCR, and search
* `open-webui` for local model management and testing
* `paperless-ai` for metadata suggestions and RAG chat
* `paperless-gpt` for LLM-assisted OCR, document enrichment, tagging, and ad hoc analysis
* internal `postgres`, `redis`, `gotenberg`, `tika`, and `ollama` backends

---

## Stack Class

Public app.

Reason:

* the routed services use `${BASE_DOMAIN}` hostnames
* routed services sit behind Traefik on `proxy`
* HTTPS is enforced on `websecure`
* access is protected with `${TRAEFIK_AUTH_MIDDLEWARE}`
* no direct host ports are exposed

---

## Routed Endpoints

* `https://${APP_HOST}.${BASE_DOMAIN}` -> Paperless UI
* `https://${OPEN_WEBUI_HOST}.${BASE_DOMAIN}` -> Open WebUI
* `https://${PAPERLESS_AI_HOST}.${BASE_DOMAIN}` -> Paperless-AI
* `https://${PAPERLESS_GPT_HOST}.${BASE_DOMAIN}` -> Paperless-GPT

All routed UIs use the shared Authentik middleware. The internal backends stay off `proxy`.

---

## Environment

Checked-in non-secret settings live in [`.env`](/home/tim/stacks/apps/paperless/.env).

This stack also requires secrets in `shared/.env.secrets`:

* `PAPERLESS_SECRET_KEY`
* `PAPERLESS_DB_PASSWORD`
* `PAPERLESS_ADMIN_USER`
* `PAPERLESS_ADMIN_PASSWORD`
* `PAPERLESS_ADMIN_MAIL` is optional but recommended
* `PAPERLESS_API_TOKEN` is optional at first boot and is used by both `paperless-ai` and `paperless-gpt`

Bootstrap note:

1. deploy the stack
2. sign into Paperless
3. create a Paperless API token
4. add `PAPERLESS_API_TOKEN` to `shared/.env.secrets`
5. run `stack up paperless` again

`paperless-ai` persists its own application settings under `./data/paperless-ai` and can be finished from its web UI after first boot.

Paperless-AI setup values:

* `Paperless-ngx API URL` -> `http://paperless:8000`
* `Ollama API URL` -> `http://ollama:11434`

Do not use `localhost` for Ollama inside Paperless-AI. The app runs in its own container, so `localhost` points back to itself and will fail.

Paperless-AI note:

* fresh boots now default `PROCESS_PREDEFINED_DOCUMENTS=no` so the app does not run empty scheduled scans before you define tags
* once Paperless-AI has bootstrapped, it persists its own settings in `./data/paperless-ai/.env` and loads that file on restart
* Paperless-AI's active Ollama model comes from that persisted runtime file via `OLLAMA_MODEL=...`; changing `apps/paperless/.env` does not override an already-bootstrapped Paperless-AI instance
* this stack patches the upstream Paperless-AI RAG startup path at container start so the `/rag` experience works correctly with the stack's normal Authentik-protected route
* when `./data/paperless-ai/system_state.json` already shows a healthy index, this stack reuses that persisted RAG state on container restart instead of forcing a fresh blocking `--initialize` path
* the startup patch also fixes the upstream RAG page so an unloaded Ollama model does not throw the page into a fake offline state or block a first chat request from triggering autoload
* for an already-bootstrapped stack that still has `PROCESS_PREDEFINED_DOCUMENTS=yes` with empty `TAGS`, change `PROCESS_PREDEFINED_DOCUMENTS=no` in `./data/paperless-ai/.env` and restart the stack
* only turn predefined scans back on after you have actually configured the target tags in Paperless-AI

---

## Storage

Bind mounts under this stack directory:

* `./data/paperless/*` -> Paperless state, media, exports, consume
* `./data/postgres` -> PostgreSQL data
* `./data/redis` -> Redis append-only state
* `./data/ollama` -> Ollama models
* `./data/open-webui` -> Open WebUI state
* `./data/paperless-ai` -> Paperless-AI state
* `./data/paperless-gpt/prompts` -> Paperless-GPT prompts

These paths stay inside the stack so backups remain scoped.

Consume subdirectories currently in use:

* `./data/paperless/consume/` -> general drop folder
* `./data/paperless/consume/scanner/` -> scanner-targeted drop folder
* `./data/paperless/consume/email/` -> reserved for mail-related intake
* `./data/paperless/consume/.stfolder/` -> Syncthing marker directory

Syncthing integration note:

* the Syncthing stack mounts `./data/paperless/consume` and `./data/paperless/export` directly so files synced from Windows can land in the same Paperless intake/export paths documented here

---

## Workflow Notes

Current Paperless workflows verified in the running stack during this session:

* `on document add` -> assigns `paperless-gpt-auto`
* `OCR for scanned documents` -> path trigger `*/scanner/**`, assigns `paperless-gpt-ocr-auto`
* `OCR for .png files` -> filename trigger `*.png`, assigns `paperless-gpt-ocr-auto`
* `OCR for .jpg files` -> filename trigger should be `*.jpg`
* `OCR for *.jpeg files` -> filename trigger `*.jpeg`
* `OCR for *.tiff files` -> filename trigger `*.tiff`

Operational notes for these workflows:

* Paperless path triggers for consume-folder files match against the full in-container path, so `scanner/**` does not work here; `*/scanner/**` does.
* Paperless filename triggers use a single glob pattern via `fnmatch`; a space-separated list like `*.jpg *.jpeg *.png` does not work as one rule.
* Overlap between `*/scanner/**` and `*.png` is currently safe because both workflows assign the same tag `paperless-gpt-ocr-auto`.

---

## Operations

Deploy or update:

```bash
stack up paperless
```

Show status:

```bash
stack ps paperless
```

View logs:

```bash
stack logs paperless
```

Validate config:

```bash
stack config paperless
```

## Notes

* This implementation intentionally drops the guide's raw `ports:` exposure in favor of Traefik routes.
* `dozzle` was not added because the repo already has stack-oriented log access.
* `ollama` is configured with `gpus: all` and expects working NVIDIA Container Toolkit support on the host.
* `paperless-gpt` starts with an empty `PAPERLESS_API_TOKEN` unless you provide one in secrets, so its automation will be incomplete until bootstrap is finished.
* `paperless-gpt` now waits idle until `PAPERLESS_API_TOKEN` is added, instead of crash-looping during first boot.
* PostgreSQL is pinned to `postgres:17` because the current bind mount layout uses the legacy `/var/lib/postgresql/data` layout.
* Ollama GPU detection was verified in-container against an NVIDIA GeForce GTX 1060 6GB.
* Paperless-AI was observed loading its persisted config from `./data/paperless-ai/.env` on `2026-03-23`, so existing installs need a one-time runtime config correction if they were bootstrapped with predefined scans enabled.
* `paperless-gpt` uses separate model roles: `PAPERLESS_GPT_LLM_MODEL` for text-only follow-up work and `PAPERLESS_GPT_VISION_MODEL` for image OCR. This stack currently uses `llama3.2:3b` for the text role and `minicpm-v:8b` for vision OCR.
* Ollama is configured with `OLLAMA_KEEP_ALIVE=30s` for this stack.
* Paperless is configured with recursive consume enabled, so files under subfolders like `consume/scanner` are ingested too.
* On this host, a cold `minicpm-v:8b` load took about 95-102 seconds and could saturate Docker/WSL disk reads while loading.
* Once warm, repeated `minicpm-v:8b` calls completed in about 1 second to reach the ready state.
* On this host, `minicpm-v:8b` unload/teardown has also repeatedly hung after completed OCR batches, with `ollama ps` stuck at `Stopping...`, GPU VRAM pinned near 5.8 GiB, and `paperless-ollama-1` continuing to burn high CPU until the stack or Ollama service is restarted.
* Before OCR-heavy sessions, consider manually warming the vision model through Open WebUI or a direct Ollama request if `minicpm-v:8b` has been idle long enough to unload.
* Paperless-ngx native OCR remains the safer primary path for bulk ingestion, while `paperless-gpt` OCR is best used in prewarmed sessions on this host.

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
* this stack patches the upstream Paperless-AI RAG startup path at container start so the `/rag` experience works correctly with the stack's normal Authentik-protected route
* when `./data/paperless-ai/system_state.json` already shows a healthy index, this stack reuses that persisted RAG state on container restart instead of forcing a fresh blocking `--initialize` path
* the startup patch also fixes the upstream RAG page so an unloaded Ollama model does not throw the page into a fake offline state or block a first chat request from triggering autoload
* for an already-bootstrapped stack that still has `PROCESS_PREDEFINED_DOCUMENTS=yes` with empty `TAGS`, run [`apps/paperless/bin/disable-paperless-ai-predefined-scan.sh`](/home/tim/stacks/apps/paperless/bin/disable-paperless-ai-predefined-scan.sh)
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

Prewarm the Paperless-GPT vision model for an OCR session:

```bash
apps/paperless/bin/prewarm-vision-model.sh
```

Disable Paperless-AI predefined scans for an already-bootstrapped stack:

```bash
apps/paperless/bin/disable-paperless-ai-predefined-scan.sh
```

---

## Notes

* This implementation intentionally drops the guide's raw `ports:` exposure in favor of Traefik routes.
* `dozzle` was not added because the repo already has stack-oriented log access.
* `ollama` is configured with `gpus: all` and expects working NVIDIA Container Toolkit support on the host.
* `paperless-gpt` starts with an empty `PAPERLESS_API_TOKEN` unless you provide one in secrets, so its automation will be incomplete until bootstrap is finished.
* `paperless-gpt` now waits idle until `PAPERLESS_API_TOKEN` is added, instead of crash-looping during first boot.
* PostgreSQL is pinned to `postgres:17` because the current bind mount layout uses the legacy `/var/lib/postgresql/data` layout.
* Ollama GPU detection was verified in-container against an NVIDIA GeForce GTX 1060 6GB.
* Paperless-AI was observed loading its persisted config from `./data/paperless-ai/.env` on `2026-03-23`, so existing installs need a one-time runtime config correction if they were bootstrapped with predefined scans enabled.
* `paperless-gpt` text generation is configured for `llama3.2:3b`; OCR vision uses `minicpm-v:8b`.
* Ollama is configured with `OLLAMA_KEEP_ALIVE=5m` for this stack.
* On this host, a cold `minicpm-v:8b` load took about 95-102 seconds and could saturate Docker/WSL disk reads while loading.
* Once warm, repeated `minicpm-v:8b` calls completed in about 1 second to reach the ready state.
* Use [`apps/paperless/bin/prewarm-vision-model.sh`](/home/tim/stacks/apps/paperless/bin/prewarm-vision-model.sh) before OCR sessions if the vision model has been idle long enough to unload.
* Paperless-ngx native OCR remains the safer primary path for bulk ingestion, while `paperless-gpt` OCR is best used in prewarmed sessions on this host.

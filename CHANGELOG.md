# CHANGELOG


> This changelog tracks infrastructure-level changes only.
> For runbooks, see `docs/runbooks/`.
> For incidents, see `docs/incidents/`.
> For stack-specific details, see `apps/<stack>/README.md`.

## Rules for agents

- Add new version entries at the top, not the bottom.
- Only record changes actually made in the current task/session.
- Do not rewrite historical entries unless fixing a factual error.
- Do not include full procedures, incident reports, or trivial formatting changes.
- Use only the sections that apply: `Added`, `Changed`, `Fixed`, `Removed`, `Notes`.

## 3.9.78 Remove IPTVnator Stack

### Changed
- `stack` no longer registers `iptvnator` as a managed stack or includes it in the `all` operation order
- `docs/tooling/stack-cli.md` replaces `iptvnator` examples with `metube` so operator docs only reference existing stacks

### Removed
- `apps/iptvnator/` and its checked-in stack definition from the repo

## 3.9.77 Nextcloud Direct Auth Routing

### Changed
- `apps/nextcloud/compose.yml` keeps `nextcloud.timopoly.com` off the shared Traefik Authentik middleware so native Nextcloud clients and WebDAV can authenticate directly against Nextcloud
- `apps/nextcloud/README.md` now documents the direct-auth routing model and the reason the shared middleware is intentionally absent
- `docs/reference/known-exceptions.md` now records `nextcloud` as a public-route-without-shared-auth exception

### Notes
- `nextcloud` still remains HTTPS-only behind Traefik; this change only removes the proxy-layer Authentik gate for that route
- the bootstrap admin env vars in `shared/.env.secrets` are first-install values only and do not rotate an already-created Nextcloud admin password

## 3.9.76 Add Nextcloud Stack

### Added
- `apps/nextcloud/` adds a repo-native public Nextcloud stack with Traefik routing, internal MariaDB and Redis services, and service-catalog metadata

### Changed
- `bin/stack` now treats `nextcloud` as a managed secret-backed stack so shared secrets are loaded automatically
- `docs/tooling/stack-cli.md` now documents `nextcloud` in the secret-backed stack list

### Notes
- the stack follows the official `nextcloud/docker` Apache deployment model while adapting it to the repo's Traefik-first public-app contract
- required credentials are expected in `shared/.env.secrets` as `NEXTCLOUD_DB_PASSWORD`, `NEXTCLOUD_DB_ROOT_PASSWORD`, `NEXTCLOUD_ADMIN_USER`, and `NEXTCLOUD_ADMIN_PASSWORD`

## 3.9.75 Add Jellyfin Stack

### Added
- `apps/jellyfin/` adds a repo-native Jellyfin stack with Traefik routing, stack-local state directories, and shared auth middleware

### Changed
- `apps/jellyfin/compose.yml` now mounts the Windows media libraries from `/mnt/d/Torrent/Movies`, `/mnt/d/Torrent/Anime`, and `/mnt/d/Torrent/Shows`

### Fixed
- `apps/jellyfin/compose.yml` no longer forces UID/GID `1000:1000`, which was preventing Jellyfin from creating `/config/log` on the existing bind-mounted config path

### Notes
- the Jellyfin stack follows the official container guidance for `/config`, `/cache`, and media mounts while adapting web access to the repo's Traefik-first model

## 3.9.74 Stack CLI Validation And Navigation

### Added
- `stack validate <stack|all>` adds an operator-facing validation command that runs compose render checks through the wrapper and then applies repo policy validation
- `stack cd <stack>` adds stack-directory navigation through the sourced shell wrapper while keeping `bin/stack` as the executable backend

### Changed
- `bin/validate-compose-policy.sh` now supports targeted paths, includes `gateway`, treats `:latest` as a warning, and suppresses direct-port warnings for documented exceptions
- docs now describe `stack validate` as the primary post-change validation path and document the `stack` shell-function layer needed for `stack cd`

### Removed
- removes the legacy `stackcd` and `stackbackup` shell helpers in favor of `stack cd ...` and `stack backup ...`

## 3.9.73 Restore Paperless Stack

### Added
- `apps/paperless/` restores the repo-native Paperless-ngx stack with Ollama, Open WebUI, Paperless-AI, and Paperless-GPT integration adapted from `timothystewart6/paperless-stack`

### Changed
- `bin/stack` now treats `paperless` as a managed secret-backed stack again

### Notes
- the restored stack keeps the repo's Traefik-first deployment model and shared-secret wiring instead of the upstream raw port-published compose

## 3.9.72 Remove Paperless Stack

### Changed
- `bin/stack` no longer treats `paperless` as a managed secret-backed stack

### Removed
- `apps/paperless/` and its checked-in stack definition from the repo
- the local `apps/paperless/` runtime contents from disk

## 3.9.71 Paperless GPT Auto OCR Resume State

### Changed
- `apps/paperless/compose.yml` now provisions a persistent state volume for the stack-local `paperless-gpt-auto-ocr` worker so it can resume an in-flight OCR job after a worker restart
- `apps/paperless/README.md` now documents the persisted worker state volume for restart resume behavior

### Fixed
- `apps/paperless/bin/paperless-gpt-auto-ocr-worker.py` now resumes its last submitted OCR job after a worker restart instead of forgetting which tagged document should receive the completed OCR text

## 3.9.70 Paperless GPT Auto OCR Worker

### Added
- `apps/paperless/bin/paperless-gpt-auto-ocr-worker.py` adds a stack-local auto OCR worker that watches the Paperless `paperless-gpt-ocr-auto` tag, submits OCR through the observable Paperless-GPT job API, and writes OCR text back to Paperless

### Changed
- `apps/paperless/compose.yml` now runs an internal-only `paperless-gpt-auto-ocr` worker service for auto OCR
- `apps/paperless/.env` now keeps the upstream inline auto OCR worker disabled while configuring the stack-local worker to watch `paperless-gpt-ocr-auto`
- `apps/paperless/README.md` now documents that auto OCR is handled by the stack-local worker and that it clears the auto tag after completion

### Fixed
- restores auto OCR as a usable primary workflow on this host by routing it through the same observable job API path used by manual OCR instead of the upstream inline worker path

## 3.9.69 Paperless GPT Auto OCR Default Gate

### Changed
- `apps/paperless/.env` now disables the checked-in `paperless-gpt` auto OCR tag by default so new deploys do not route documents into the current invisible inline Ollama OCR worker path
- `apps/paperless/README.md` now documents that manual OCR remains supported and that auto OCR must be explicitly re-enabled

### Notes
- operators who want auto OCR back must restore `PAPERLESS_GPT_AUTO_OCR_TAG=paperless-gpt-ocr-auto` and align the Paperless workflow tag with that value

## 3.9.68 Paperless-AI RAG Startup Fix

### Changed
- `apps/paperless/compose.yml` now starts `paperless-ai` through a stack-local patch script and mounts that script read-only into the container
- `apps/paperless/README.md` now documents the stack-local Paperless-AI RAG startup fixes
- `apps/paperless/bin/start-paperless-ai-with-rag-fixes.sh` patches the upstream Paperless-AI RAG startup path at container start
- `apps/paperless/bin/start-paperless-ai-with-rag-fixes.sh` now reuses a healthy persisted `data/paperless-ai/system_state.json` on restart instead of always forcing Python RAG `--initialize`
- `apps/paperless/bin/start-paperless-ai-with-rag-fixes.sh` now patches the upstream RAG page so `ai_model: null` is treated as idle instead of crashing the status check, and so the page does not block first-send on stale offline state

### Fixed
- avoids recreates getting stuck with `connect ECONNREFUSED 127.0.0.1:8000` when the upstream Python RAG startup path would otherwise block before opening the port
- fixes the frontend-only failure where unloaded Ollama state kept `/rag` stuck offline in the browser and prevented the first request from autoloading `llama3.2:3b`

---
## 3.9.67 Paperless GPT OCR Session Prewarm

### Changed
- `apps/paperless/compose.yml` now sets `OLLAMA_KEEP_ALIVE=5m` on the Ollama service instead of running an always-on vision-model keepwarm sidecar
- `apps/paperless/.env` now uses `PAPERLESS_OLLAMA_KEEP_ALIVE=5m` and drops the always-on warm-interval setting
- `apps/paperless/README.md` now documents the session-prewarm workflow and the observed cold-load versus warm-load timings on this host
- `apps/paperless/service.meta.json` describes `paperless-gpt` as OCR plus analysis again
- `apps/paperless/bin/prewarm-vision-model.sh` adds a stack-local warmup command for OCR sessions

### Fixed
- keeps `paperless-gpt` OCR operational on this host without reserving VRAM all day, while still avoiding first-request cold loads during planned OCR sessions

### Notes
- `paperless-gpt` remains OCR-capable; operators can prewarm the vision model on demand before OCR sessions

---

## 3.9.66 Web UI Style Reuse Guidance

### Changed
- `docs/checklists/new-stack.md` now tells new browser-facing stacks to reuse the landing stylesheet pattern by default
- `docs/policies/compose-contract.md` now documents the landing stylesheet reuse convention for custom web UIs

### Notes
- new stack guidance now treats `apps/landing/site/timopoly-ui.css` as the default visual baseline for repo-managed web UIs

---

## 3.9.65 Landing Live Catalog Refresh

### Changed
- `apps/landing/compose.yml` now mounts the shared `service-catalog` directory instead of binding only `services.json`
- `apps/landing/site/index.html` now reads `/service-catalog/services.json` so landing sees atomic catalog rewrites without a container restart
- `apps/landing/README.md` now documents the directory-backed catalog path and no-restart refresh behavior

### Notes
- landing no longer requires a manual recreate just to pick up generated service-catalog updates

---

## 3.9.64 Service Metadata Validation Coverage

### Added
- `service.meta.json` files for the remaining checked-in public stacks that previously lacked metadata coverage

### Changed
- `bin/validate-compose-policy.sh` now validates public hostname coverage and stale entries for `apps/<stack>/service.meta.json`
- `docs/reference/agent-onboarding.md` now tells agents to inspect `service.meta.json` for public stacks

### Notes
- compose policy validation now fails early when a public stack is missing service metadata or contains stale hostname keys

---

## 3.9.63 Per-Stack Service Metadata Policy

### Added
- per-stack `service.meta.json` files for the current public stacks under `apps/`
- public-stack creation guidance for `service.meta.json` in `docs/checklists/new-stack.md`
- service-catalog metadata contract and template in `docs/policies/compose-contract.md`

### Changed
- `bin/generate-service-catalog` now aggregates metadata from `apps/*/service.meta.json`
- `docs/architecture/service-catalog.md` now documents the per-stack metadata model and `CF_SERVICE_CATALOG_META_DIR`

### Removed
- `apps/landing/services.meta.json` in favor of per-stack `service.meta.json` files

### Notes
- public stack presentation metadata now lives with each stack instead of a single landing-owned file

---

## 3.9.62 Landing Shared Catalog Integration

### Changed
- `apps/landing/compose.yml` now mounts `shared/service-catalog/services.json` as the runtime `/services.json` source
- `apps/landing/site/index.html` now reads the generated service-catalog schema, hides the `www.timopoly.com` self-entry, and shows the catalog `generated_at` timestamp
- `apps/landing/README.md` now documents the shared catalog mount and generated runtime data flow

### Fixed
- `bin/generate-service-catalog` now writes `shared/service-catalog/services.json` with readable file permissions so Nginx can serve it from the landing stack

### Notes
- the checked-in static `apps/landing/site/services.json` file is no longer the active runtime source for landing

---

## 3.9.61 Service Catalog Automation

### Added
- automatic hostname-level change logging for `bin/generate-service-catalog` in `state/logs/service-catalog-changes.log`

### Changed
- `bin/generate-service-catalog` now loads missing Cloudflare credentials from `shared/.env.secrets` by default
- `bin/generate-service-catalog` now skips rewriting `shared/service-catalog/services.json` when the generated catalog content is unchanged
- documented the service-catalog cron workflow, env-file lookup, and change-log behavior in `docs/architecture/service-catalog.md`

### Notes
- a user crontab entry now runs `bin/generate-service-catalog` every 10 minutes to refresh `shared/service-catalog/services.json`
- service-catalog generation remains separate from the landing stack; landing is not wired to consume the shared artifact by this change

---

## 3.9.60 Docs Cleanup, Authentik README, and Breakglass Removal

### Added
- `apps/authentik/README.md` documenting the checked-in Authentik stack config
- `apps/gitea/README.md` documenting the checked-in Gitea stack config
- `apps/landing/README.md` documenting the checked-in landing stack config
- `docs/reference/agent-onboarding.md` as a start-of-session guide for new agents

### Changed
- `docs/README.md` now links only to documentation files that currently exist in the repo
- `ai-context.md` rewritten as supplemental orientation instead of primary repo truth
- `AGENTS.md` now links to the agent onboarding guide
- `docs/reference/known-exceptions.md` populated with verified repo-specific exceptions for adguardhome, syncthing, qbittorrentvpn, authentik, and gateway

### Removed
- `apps/breakglass/compose.yml`
- `apps/breakglass/` stack directory

### Notes
- This entry records only changes made in the current session
- `bin/generate-service-catalog` and `docs/architecture/service-catalog.md` exist in the repo but are not yet integrated into application stacks
- service-catalog metadata/output flow is documented, but current consumers are not wired to use it

---

## 3.9.59 Infrastructure Policy & AI-Agent Enablement

### Added
- AGENTS.md rewritten as enforceable policy and constraint layer
- Compose contract defining standard stack structure
- Routing contract defining Traefik, hostname, and middleware rules
- Environment contract defining variable scope and secret handling
- New stack checklist for consistent stack creation
- Public app publish runbook
- Traefik debugging runbook
- Known exceptions registry for intentional policy deviations
- Initial compose policy validation script

### Changed
- Standardized repository structure toward policy → contract → runbook → validation model
- Clarified stack classification: public, LAN-only, internal-only
- Formalized routing, networking, and security expectations

### Notes
- Existing stacks may not yet fully comply with new policies
- Validation script is heuristic (v1) and will be improved
- service-catalog is excluded from this change and policy scope

---

## 3.9.58

### Added
- nodecast-tv stack (IPTV web player with Traefik routing)

### Changed
- Documented Cloudflare Tunnel → Traefik HTTPS origin pattern
  - Use Origin Server Name + SNI instead of disabling TLS verification
  - Prevents 502 errors when routing through cloudflared

### Fixed
- Cloudflare Tunnel 502 when using HTTPS origin (`gateway_traefik:443`)
  - Root cause: TLS hostname mismatch (`gateway_traefik` vs app domain)
  - Solution:
    - Origin Server Name = <app-domain>
    - Match SNI to Host = ON
    - No TLS Verify = OFF

---

## 3.9.57

### Added

* Automatic recovery workflow for dead qBittorrentVPN WireGuard tunnels
* `qb-vpn-refresh` (host-level repair command)
* `qb-vpn-watchdog` (self-healing watchdog)
* Watchdog runtime state directory:

  * `~/stacks/state/qbittorrentvpn/`
* Cron-based watchdog scheduling in WSL
* Stack registry entry:

  * `yttranscript -> ~/stacks/apps/yttranscript/compose.yml`

### Changed

#### qBittorrentVPN

* Introduced self-healing model:

  * detection (health + logs + connectivity)
  * automated repair (config regeneration)
* Clarified separation of concerns:

  * `apps/` → stack definitions
  * `bin/` → operational tooling
  * `state/` → runtime state
  * `shared/` → secrets

#### Documentation

* Expanded qBittorrentVPN documentation:

  * dead tunnel failure mode
  * manual recovery procedure
  * watchdog + refresh workflow
  * detection + verification model

* Documented key insight:

  * WireGuard may report "connected" while passing zero traffic
  * Raw IP connectivity check is required

#### yt2midi_v3

* Parameterized stack name:

  * `name: ${APP_ID}`
* Converted build paths to relative
* Parameterized Traefik naming:

  * `${APP_ID}`
  * `${APP_HOST}`
  * `${TRAEFIK_CERTRESOLVER:-cloudflare}`
* Parameterized timezone:

  * `TZ=${TZ:-Europe/Berlin}`
* Converted data mounts:

  * `./data/in`
  * `./data/out`

### Removed

* `apps/qbittorrentvpn/backup_compose`

---

## 3.9.56

### Added

* Stack toolchain documentation section:

  * `STACK TOOLCHAIN (stack / stk / stackbackup)`

### Changed

* Documented operational tooling in:

  * `~/stacks/bin/`

* Documented tools:

  * `stack` → primary CLI
  * `stk` → shortcut wrapper
  * `stackbackup` → backup helper

* Updated workflow:

  * Use `stack <command> <stack>`
  * Deprecated `./stack`

* Documented:

  * automatic stack discovery
  * backup strategy

---

## 3.9.55

### Added

* New stack management tooling:

  * `/home/tim/stacks/bin/`

* Primary CLI:

  * `stack`

* Alias:

  * `stk`

* Stack listing:

  * `stack list`

* Backup tooling:

  * `stackbackup`

### Changed

* Replaced:

  * `./stack` → `stack`

* Implemented automatic stack discovery:

  * `~/stacks/apps/*/compose.yml`
  * `~/stacks/gateway/compose.yml`

* Added shell integration:

  * PATH update
  * `stack-tools.sh` sourcing

### Details

* Backup location:

  * `~/stacks/backups/apps/<stack>/`

* Safety:

  * `stackbackup` only runs inside stack directory

---

## 3.9.54

### Added

* New stack: `yt2midi_v3`

#### Architecture

* UI container (nginx)
* API container (CUDA backend)

#### GPU

* `gpus: all`
* Base image:

  * `nvidia/cuda:11.8.0-runtime-ubuntu22.04`

#### Storage

* `/data/in`
* `/data/out`

#### Networking

* `internal`
* `proxy`

#### Traefik

* Host:

  * `yt2midi-v3.${BASE_DOMAIN}`

* EntryPoint:

  * `websecure`

* TLS:

  * cloudflare resolver

* Backend:

  * port 80

* Authentik middleware:

  * `${TRAEFIK_AUTH_MIDDLEWARE}`

### Changed

* Updated stack wrapper:

  * added:

    * `landing`
    * `yt2midi_v3`

* Immich routing (temporary):

  * Auth middleware disabled for testing

---

## 3.9.53

### Added

* Landing page:

  * `www.timopoly.com`

---

## 3.9.52

### Changed

#### Cloudflare Tunnel

* Migrated to token-based tunnel (remote-managed)

* Removed config.yml-based routing

* cloudflared now runs with:

  * `tunnel --no-autoupdate run --token`

* Tunnel routing moved to Cloudflare dashboard

* cloudflared attached to `proxy` network

#### Validation

* Verified QUIC connectivity
* Confirmed routing:

  * Cloudflare → Tunnel → Traefik → Services

#### MeTube

* Temporarily disabled Authentik middleware for testing
* Verified external routing works

---

## 3.9.51

### Added

#### HTTPS Migration (Production)

* Switched to Let's Encrypt production
* DNS-01 challenge via Cloudflare
* Verified certificate chain (R12)

#### Traefik HTTPS-first

* `websecure` as primary entrypoint
* HTTP → HTTPS redirect enforced
* Removed redundant HTTP entrypoints

#### Cloudflare Tunnel Alignment

* Confirmed tunnel → Traefik → service flow
* Validated TLS compatibility

#### Authentik

* Re-enabled ForwardAuth
* Verified callback routing
* Verified correct post-login redirects

---

## 3.9.50

### Added

#### Global Authentication System

* Authentik stack:

  * server
  * worker
  * postgres
  * redis
  * proxy outpost

* Traefik ForwardAuth integration

* Middleware chain:

  * `authentik-forwardauth`
  * `authentik-errors`

#### Routing Model

* `auth.${BASE_DOMAIN}` → UI
* `/outpost.goauthentik.io/` → proxy

#### Configuration

* Global middleware:

  * `TRAEFIK_AUTH_MIDDLEWARE=authentik-chain@file`

### Validated

* ForwardAuth flow
* Redirect behavior
* Required host alignment
* Outpost routing requirements

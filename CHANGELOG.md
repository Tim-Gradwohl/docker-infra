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


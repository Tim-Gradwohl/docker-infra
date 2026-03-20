# AI CONTEXT — TIMOPOLY DOCKER STACK

## REPOSITORY

Primary repository:
https://github.com/Tim-Gradwohl/docker-infra

Use this repository as the source of truth.
If additional context is required, request specific files.

---

## SYSTEM OVERVIEW

Single-host homelab infrastructure running on:

* Windows 11 + Docker Desktop (WSL2 backend)
* Linux containers only (no Windows containers)
* Docker Compose (no Kubernetes)

Core model:

Internet
→ Cloudflare Edge
→ Cloudflare Tunnel (cloudflared)
→ Traefik (gateway)
→ Authentik (ForwardAuth)
→ Docker services

LAN:

Clients
→ AdGuard DNS
→ Traefik
→ Docker services

---

## CORE ARCHITECTURE

### Stack layout

* `apps/` → compose stacks (source of truth)
* `gateway/` → Traefik + dynamic config
* `bin/` → host-level tooling (stack CLI, watchdogs)
* `state/` → runtime state (watchdogs, logs)
* `shared/` → env + secrets

### Networking

* `proxy` → shared external network for Traefik routing
* `internal` → per-stack internal communication

Rules:

* No direct container exposure
* All HTTP goes through Traefik
* DNS-controlled routing (host-based)

---

## INGRESS MODEL

### WAN (public)

Cloudflare DNS
→ Cloudflare Tunnel
→ Traefik (:443)
→ service

* No inbound ports required
* TLS handled via Traefik (DNS-01)

### LAN (internal)

AdGuard DNS (*.lan domain)
→ resolves to host IP
→ Traefik
→ service

* Split-horizon DNS
* Same hostnames usable internally

---

## AUTHENTICATION MODEL

* Authentik via Traefik ForwardAuth
* Middleware chain:

  `authentik-forwardauth → authentik-errors`

Rules:

* Never protect Authentik itself
* Outpost endpoints must route to `authentik_proxy`
* HTTPS must be enforced BEFORE auth flow

Critical fix:

* Cloudflare “Always Use HTTPS” required to avoid callback failures

---

## TOOLING

### Primary CLI

```
stack <command> <stack>
```

Examples:

* `stack up immich`
* `stack down metube`
* `stack logs immich`
* `stack list`

Shortcut:

```
stk <command>
```

### Backup

```
cd ~/stacks/apps/<stack>
stackbackup
```

* Output: `.tar.zst`
* Location: `~/stacks/backups/apps/<stack>/`

### Rules

* Always use `stack` (not raw docker compose)
* Env files must always be loaded:

  * `.env.global`
  * `.env.secrets` (if required)

---

## DEPLOYMENT MODEL

Golden rules:

* Git = source of truth
* `stack` = only deployment interface
* Never rely on memory for env variables

Flow:

1. Modify compose
2. Commit + push
3. `stack up <stack>`

---

## QBITTORRENTVPN (CRITICAL SYSTEM)

### Architecture

* gluetun (VPN)
* qBittorrent (shares gluetun network)
* PIA port forwarding containers
* port-sync (updates qBittorrent port)

### Enforcement

```
network_mode: service:gluetun
```

→ no VPN = no connectivity

---

## CRITICAL FAILURE MODE

### Dead WireGuard tunnel

Symptoms:

* gluetun unhealthy
* DNS failures / timeouts
* ping 1.1.1.1 fails
* WireGuard shows “connected” but no traffic

Root cause:

* stale / broken endpoint in `wg0.conf`

---

## RECOVERY MODEL

### Manual

```
stk down qbittorrentvpn
rm wireguard-pia/wg0.conf
# regenerate config via PIA container
stk up qbittorrentvpn
```

Validate:

```
docker exec qbittorrentvpn_gluetun ping -c1 1.1.1.1
```

---

### Automated

#### qb-vpn-refresh

* regenerates WireGuard config
* restarts stack

#### qb-vpn-watchdog

* detects failure via:

  * unhealthy container
  * log pattern
  * failed connectivity
* triggers refresh
* verifies recovery

Runs via cron.

---

## DEBUG PLAYBOOK (FAST PATHS)

### Traefik 404

Check:

* container running
* attached to `proxy` network
* labels correct
* Traefik logs

---

### Authentik login fails (400)

Cause:

* HTTP/HTTPS mismatch

Fix:

* enforce HTTPS at Cloudflare edge

---

### VPN issues

Check:

```
ping 1.1.1.1 inside gluetun
```

If fail:
→ regenerate `wg0.conf`

---

## EXPOSURE MODEL

### Public

* Only Traefik (:80 / :443)

### LAN only

* DNS (AdGuard :53)
* restricted services via middleware

### Never exposed

* DBs
* internal service ports
* container direct access

---

## TRUST BOUNDARIES

1. WAN (untrusted)
2. Cloudflare edge
3. host (192.168.x.x)
4. Docker networks
5. LAN

Only Traefik is reachable from WAN.

---

## CONSTRAINTS

* WSL2 environment
* Docker Compose only
* No Kubernetes
* Consumer hardware
* NAT / no static IP

---

## IMPORTANT RULES

* Do not expose containers directly
* Do not bypass Traefik
* Do not run docker compose without env files
* Do not modify unrelated stacks
* Always validate connectivity at raw IP level (not DNS)

---

## MENTAL MODEL

* Traefik = single entrypoint
* Cloudflare = external routing layer
* Authentik = access control
* Docker = execution layer
* AdGuard = internal DNS authority

---

## WHERE TO FIND DETAILS

* Architecture → `docs/architecture/`
* Runbooks → `docs/runbooks/`
* Stack-specific → `apps/<stack>/README.md`
* Incidents → `docs/incidents/`

---

## REPOSITORY MAP

### Core files
- AGENTS.md → rules for agents
- ai-context.md → system overview
- CHANGELOG.md → change history

### Architecture
- docs/architecture/
  - overview.md
  - networking.md
  - ingress-cloudflare-traefik.md
  - authentik.md

### Runbooks
- docs/runbooks/
  - qbittorrentvpn-recovery.md
  - traefik-debug.md
  - authentik-debug.md

### Stacks
- gateway/README.md → Traefik + ingress
- apps/cloudflared/README.md → Cloudflare Tunnel
- apps/adguardhome/README.md → DNS
- apps/qbittorrentvpn/README.md → VPN stack
- apps/immich/README.md → photo service
- apps/metube/README.md → yt-dlp UI
- apps/yt2midi_v3/README.md → GPU pipeline

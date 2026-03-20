# Overview

Environment:

* Windows 11 + Docker Desktop (WSL2 backend)
* Docker Engine inside WSL2
* Linux containers only

Core model:

Internet
→ Cloudflare Edge
→ Cloudflare Tunnel
→ Traefik
→ Authentik
→ Services

LAN:

AdGuard DNS
→ Traefik
→ Services

Principles:

* Single entrypoint (Traefik)
* No direct container exposure
* Host-based routing
* Git-backed infrastructure


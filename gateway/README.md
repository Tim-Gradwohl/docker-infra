# Gateway (Traefik)

## Purpose

The gateway stack provides the **single ingress point** for all HTTP(S) traffic.

Responsibilities:

* Reverse proxy (Traefik)
* TLS termination (Let's Encrypt / Cloudflare DNS-01)
* Routing to services via Docker labels
* Authentication enforcement (Authentik ForwardAuth)
* Integration with Cloudflare Tunnel

---

## Architecture

Traffic flow:

Internet
→ Cloudflare Edge
→ Cloudflare Tunnel (`cloudflared`)
→ Traefik (`gateway_traefik`)
→ Target service

LAN:

AdGuard DNS
→ Traefik
→ Target service

Key properties:

* Single entrypoint for all services
* No direct container exposure
* Host-based routing only

---

## Components

### Traefik

Container:

* `gateway_traefik`

Image:

* `traefik:v3`

Providers:

* Docker (labels)
* File provider (dynamic config)

---

## Entrypoints

* `web` → :80

  * Redirects to HTTPS

* `websecure` → :443

  * Primary entrypoint
  * TLS enabled

---

## TLS

* ACME DNS-01 via Cloudflare
* Wildcard certificates supported
* Storage:

  * `/home/tim/stacks/gateway/acme/acme.json`

Notes:

* Internal Docker traffic may use Traefik default cert
* `cloudflared` uses `noTLSVerify=true` internally

---

## Networking

Attached networks:

* `proxy` (required for routing)

Rules:

* All routed services must join `proxy`
* Traefik must see containers via Docker provider

---

## Routing Model

* Defined via Docker labels on services
* Uses host-based routing:

Example:

```text
Host(service.${BASE_DOMAIN})
```

Requirements for routing:

* `traefik.enable=true`
* correct `traefik.docker.network=proxy`
* correct service port

---

## Authentication (Authentik)

* Implemented via ForwardAuth middleware
* Uses `authentik_proxy` (outpost)

Global middleware:

```text
${TRAEFIK_AUTH_MIDDLEWARE}
```

Rules:

* Do NOT apply auth to Authentik itself
* Outpost endpoints must route to `authentik_proxy`
* HTTPS must be enforced before auth flow

---

## Cloudflare Tunnel

Container:

* `cloudflared`

Role:

* exposes services externally without opening ports
* forwards traffic to Traefik over Docker network

Key properties:

* token-based tunnel
* ingress controlled in Cloudflare dashboard
* default deny (404)

---

## Dynamic Configuration

Location:

```text
/home/tim/stacks/gateway/dynamic/
```

Examples:

* middlewares
* TLS settings
* shared config

Important:

* `watch=false`
* requires Traefik restart after changes

---

## Operations

### Deploy / restart

```bash
stack up gateway
```

### Logs

```bash
stack logs gateway
```

### Restart after config change

```bash
docker restart gateway_traefik
```

---

## Debugging

### Route returns 404

Check:

* container running
* attached to `proxy` network
* correct Traefik labels
* Traefik logs

---

### Authentik login fails (400)

Cause:

* HTTP/HTTPS mismatch

Fix:

* enable Cloudflare "Always Use HTTPS"

---

### Service not reachable

Check:

* service port matches Traefik config
* router rule correct
* container healthy

---

## Security Model

* Only Traefik exposed externally
* No direct container ports
* Auth enforced at proxy layer
* LAN-only services use IP allowlist middleware

---

## Constraints

* Docker Compose only (no Swarm/K8s)
* WSL2 environment
* Single host deployment
* NAT / Cloudflare Tunnel for external access

---

## References

* Architecture → `docs/architecture/`
* Auth → `docs/architecture/authentik.md`
* Ingress → `docs/architecture/ingress-cloudflare-traefik.md`
* Debug → `docs/runbooks/`
* System context → `ai-context.md`


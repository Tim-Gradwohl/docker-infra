# Gateway / Traefik Architecture

## Overview

Traefik is the single entrypoint for all HTTP/HTTPS traffic.

- All apps are routed via Traefik
- No direct port exposure
- Cloudflare Tunnel forwards external traffic to Traefik

---

## Cloudflare Tunnel → Traefik (HTTPS origin pattern)

Service:
https://gateway_traefik:443

TLS settings (per route):
Origin Server Name = <app-domain>
Match SNI to Host = ON
No TLS Verify = OFF

Example:
Origin Server Name = tv.timopoly.com

### Why

- Traefik selects certificates via SNI (hostname)
- cloudflared connects to `gateway_traefik`, which does not match the certificate hostname
- without override → TLS verification fails → 502

### Do NOT use

No TLS Verify = ON  
→ only for temporary debugging

### Alternative (simpler internal routing)

http://gateway_traefik:80

---

## Routing Model

- Each app defines a Traefik router via labels
- Host-based routing: Host(<subdomain>.<BASE_DOMAIN>)
- TLS termination handled by Traefik (Let's Encrypt / DNS challenge)
- Auth handled via Authentik ForwardAuth middleware

---

## Principles

- Single ingress (Traefik)
- No direct container exposure
- Explicit routing via labels
- Reusable patterns across all stacks

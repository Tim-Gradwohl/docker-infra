# Ingress Model

## WAN

Cloudflare
→ Tunnel
→ Traefik (:443)
→ service

* No inbound ports required
* TLS via DNS-01

## LAN

AdGuard DNS
→ host IP
→ Traefik
→ service

## Key property

Split-horizon DNS:

* same hostname works LAN + WAN


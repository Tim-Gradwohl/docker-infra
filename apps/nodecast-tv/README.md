# nodecast-tv

## Purpose
nodecast-tv provides a web-based IPTV player for:
- Live TV
- EPG / TV Guide
- Movies (VOD)
- Series

## Container
- `nodecast-tv`

Upstream:
- `technomancer702/nodecast-tv`

## Networking
Network:
- `proxy`

Rules:
- no direct port exposure
- all access via Traefik

## Routing
Defined via Traefik labels.

Example:
    Host(tv.${BASE_DOMAIN})

## Service Port
Internal container port:
    3000

## Storage
Bind mounts:
- `./data -> /app/data`

Contains:
- application state
- database
- playlists / provider configuration

## Cloudflare Tunnel

When using Cloudflare Tunnel with HTTPS origin to Traefik:

- Service: `https://gateway_traefik:443`
- Origin Server Name: `tv.${BASE_DOMAIN}`
- Match SNI to Host: `ON`
- No TLS Verify: `OFF`

Without correct origin TLS settings, Cloudflare may return `502` even when the app and Traefik routing are healthy.

See: `docs/architecture/gateway.md`

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
```text
Host(tv.${BASE_DOMAIN})

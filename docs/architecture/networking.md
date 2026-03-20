# Networking

## Networks

* `proxy`

  * external bridge network
  * used by Traefik and routed services

* `internal`

  * per-stack communication
  * not externally accessible

## Rules

* All HTTP traffic must go through Traefik
* Services must attach to `proxy` for routing
* No macvlan or host networking

## Special case

* qBittorrent uses:
  network_mode: service:gluetun


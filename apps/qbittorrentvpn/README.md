# qBittorrentVPN

## Purpose

Run qBittorrent behind PIA WireGuard using Gluetun.

## Components

* gluetun
* qbittorrent
* pia-pf
* pf-writer
* port-sync

## Enforcement

network_mode: service:gluetun

→ ensures VPN-only traffic

## Failure mode

Dead WireGuard tunnel

See:
../../docs/runbooks/qbittorrentvpn-recovery.md


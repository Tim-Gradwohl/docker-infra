# Jellyfin

## Purpose

Jellyfin provides a self-hosted media server UI for browsing and streaming the local media library.

This stack adapts the official container guidance to the repo's Traefik-first model.

Configured libraries:

* Movies -> `/movies` from `/mnt/d/Torrent/Movies`
* Anime -> `/anime` from `/mnt/d/Torrent/Anime`
* Shows -> `/shows` from `/mnt/d/Torrent/Shows`

---

## Stack Class

Public app.

Reason:

* routed through Traefik on `proxy`
* protected with `${TRAEFIK_AUTH_MIDDLEWARE}`
* no direct HTTP port exposure
* intended for public hostname routing on `${BASE_DOMAIN}`

---

## Container

* `jellyfin`

Image:

* `jellyfin/jellyfin:10.11`

---

## Routing

Access:

* `https://${APP_HOST}.${BASE_DOMAIN}`

Traefik forwards traffic to container port `8096`.

---

## Storage

Bind mounts:

* `./data/config` -> `/config`
* `./data/cache` -> `/cache`
* `/mnt/d/Torrent/Movies` -> `/movies` (read-only)
* `/mnt/d/Torrent/Anime` -> `/anime` (read-only)
* `/mnt/d/Torrent/Shows` -> `/shows` (read-only)

Notes:

* `./data/config` stores Jellyfin configuration and database state
* `./data/cache` stores cache/transcoding metadata
* `/movies`, `/anime`, and `/shows` are the host media libraries exposed to Jellyfin
* the stack runs with the image default user because the existing config/cache bind paths on this host are not writable by UID/GID `1000:1000`

---

## Operations

Deploy or update:

```bash
stack up jellyfin
```

Show status:

```bash
stack ps jellyfin
```

View logs:

```bash
stack logs jellyfin
```

Validate:

```bash
stack validate jellyfin
```

---

## Notes

* the stack uses the official `JELLYFIN_PublishedServerUrl` setting so clients see the Traefik URL instead of the internal container address
* DLNA is not enabled in this repo-native stack because the Jellyfin docs require host networking for DLNA, which is outside the normal repo policy
* UDP autodiscovery is also not exposed by default; clients should connect with the configured hostname
* startup was verified with `stack doctor jellyfin`; the earlier `/config/log` permission crash was resolved by removing the forced `user:` override

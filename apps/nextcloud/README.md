# Nextcloud

## Purpose

Nextcloud provides a public file sync and collaboration service behind Traefik.

This stack adapts the official `nextcloud/docker` Apache deployment guidance to the repo's public-app contract.

---

## Stack Class

Public app.

Reason:

* routed through Traefik on `proxy`
* HTTPS enforced on `websecure`
* no direct host HTTP port exposure
* intentionally left on Nextcloud-managed authentication so native clients and WebDAV can authenticate directly

---

## Services

* `nextcloud` -> public web app
* `mariadb` -> internal database
* `redis` -> internal cache/session backend

---

## Routing

Access:

* `https://${APP_HOST}.${BASE_DOMAIN}`

Traefik forwards to container port `80` on `nextcloud`.

The stack sets the official reverse-proxy environment values so Nextcloud generates external URLs for the public hostname:

* `NEXTCLOUD_TRUSTED_DOMAINS`
* `TRUSTED_PROXIES`
* `OVERWRITEHOST`
* `OVERWRITEPROTOCOL`
* `OVERWRITECLIURL`

---

## Storage

Bind mounts:

* `./data/nextcloud` -> `/var/www/html`
* `./data/mariadb` -> `/var/lib/mysql`
* `./data/redis` -> `/data`

Notes:

* `./data/nextcloud` holds the full application state used by the official image for upgrades and persistent data
* `./data/mariadb` holds the MariaDB data directory
* `./data/redis` holds append-only Redis persistence

---

## Secrets

This stack requires these values in `shared/.env.secrets`:

* `NEXTCLOUD_DB_PASSWORD`
* `NEXTCLOUD_DB_ROOT_PASSWORD`
* `NEXTCLOUD_ADMIN_USER`
* `NEXTCLOUD_ADMIN_PASSWORD`

Compose uses fail-fast interpolation, so missing values will stop `stack up nextcloud` and `stack validate nextcloud`.

---

## Operations

Deploy or update:

```bash
stack up nextcloud
```

Show status:

```bash
stack ps nextcloud
```

View logs:

```bash
stack logs nextcloud
```

Validate:

```bash
stack validate nextcloud
```

---

## Notes

* the checked-in stack uses the official Apache image rather than Nextcloud AIO
* MariaDB and Redis stay internal-only on the `internal` network
* the current repo-native stack does not add extra companion services such as Office, Talk, or a separate cron worker
* the public route intentionally does not use `${TRAEFIK_AUTH_MIDDLEWARE}` because native Nextcloud clients and WebDAV need to authenticate against Nextcloud itself
* upstream warns that major upgrades must be performed one major version at a time; keep that in mind when changing the pinned `nextcloud` tag

# Syncthing

## Purpose

File synchronization stack with a Traefik-routed web UI and direct L4 sync/discovery ports for Syncthing device traffic.

Provides:

* `syncthing` for device-to-device sync and web administration
* direct access to the default Syncthing data root under `./data`
* direct access to Paperless exchange folders for Windows-to-Paperless file sync

---

## Stack Class

Public app with a documented direct-port exception.

Reason:

* the web UI is routed through Traefik on `proxy`
* HTTPS is enforced on `websecure`
* access is protected with `${TRAEFIK_AUTH_MIDDLEWARE}`
* Syncthing device sync and discovery still require real host ports

---

## Storage

Bind mounts:

* `/home/tim/stacks/apps/syncthing/config` -> Syncthing config and database
* `/home/tim/stacks/apps/syncthing/data` -> default Syncthing shared folder root
* `/home/tim/stacks/apps/paperless/data/paperless/consume` -> `/paperless/consume`
* `/home/tim/stacks/apps/paperless/data/paperless/export` -> `/paperless/export`

To sync files from Windows into Paperless, add Syncthing folders that point to `/paperless/consume` and `/paperless/export` inside the container.

Use `consume` for inbound files that Paperless should ingest. Use `export` for files written out by Paperless that you want Syncthing to distribute.

---

## Operations

Deploy or update:

```bash
stack up syncthing
```

Show status:

```bash
stack ps syncthing
```

View logs:

```bash
stack logs syncthing
```

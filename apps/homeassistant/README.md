# Home Assistant

## Purpose

Home Assistant provides the main home automation UI and automation engine behind Traefik.

This stack starts from the official Home Assistant Container guidance and adapts it to the repo's public-app contract.

---

## Stack Class

Public app.

Reason:

* routed through Traefik on `proxy`
* HTTPS enforced on `websecure`
* no direct host `8123` exposure
* intentionally left on Home Assistant-managed authentication instead of `${TRAEFIK_AUTH_MIDDLEWARE}`

---

## Container

* `homeassistant`

Image:

* `ghcr.io/home-assistant/home-assistant:${HOMEASSISTANT_VERSION}`

---

## Routing

Access:

* `https://${APP_HOST}.${BASE_DOMAIN}`

Traefik forwards traffic to container port `8123`.

This route intentionally does not use `${TRAEFIK_AUTH_MIDDLEWARE}`. Home Assistant companion apps, webhooks, and the WebSocket API should terminate directly in Home Assistant instead of being gated by proxy-layer ForwardAuth.

---

## Storage

Bind mounts:

* `./data/config` -> `/config`
* `/etc/localtime:/etc/localtime:ro`
* `/run/dbus:/run/dbus:ro`

Notes:

* `./data/config` holds the Home Assistant configuration, database, and runtime state
* `/run/dbus` is mounted read-only for integrations that need D-Bus access from the container

---

## Reverse Proxy Setup

Home Assistant must trust the reverse proxy before the public route will work correctly.

Add this to `/config/configuration.yaml`:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.18.0.0/16
```

The `172.18.0.0/16` example matches the checked-in gateway trust range for forwarded headers. After changing `configuration.yaml`, restart Home Assistant.

On a first boot without this block, the public URL will typically return `400: Bad Request` and the Home Assistant logs will report that a request from a reverse proxy was received from `172.18.0.3` without reverse-proxy support being enabled.

In this stack, `/config/configuration.yaml` lives on the host at `apps/homeassistant/data/config/configuration.yaml`.

---

## Operations

Deploy or update:

```bash
stack up homeassistant
```

Show status:

```bash
stack ps homeassistant
```

View logs:

```bash
stack logs homeassistant
```

Validate:

```bash
stack validate homeassistant
```

---

## Notes

* upstream's compose example uses `privileged: true` and `network_mode: host`; this repo-native stack does not enable either by default because public HTTP traffic must stay behind Traefik
* if you later need USB radio passthrough, add only the specific `devices:` mappings you need and document that change
* host-network discovery protocols and some multicast-dependent integrations may need extra, stack-specific follow-up work because this stack stays on Docker bridge networking instead of upstream host networking

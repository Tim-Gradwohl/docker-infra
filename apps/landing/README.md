# Landing

## Purpose

This stack serves the landing page for public services.

Operator note provided in-session:

* this is the landing page for public services exposed through the Cloudflare tunnel path

The runtime and routing details below are based on the checked-in stack files.

---

## Stack Class

Public app.

Reason:

* the stack is routed through Traefik
* the router rule is `Host(\`www.timopoly.com\`)`
* the routed service joins the external `proxy` network
* the route uses `websecure` with TLS enabled

---

## Main Service

Service:

* `landing`

Image:

* `nginx:alpine`

Container name:

* `landing`

Restart policy:

* `unless-stopped`

---

## Routing

Routed service:

* `landing`

Router rule:

* `Host(\`www.timopoly.com\`)`

Entrypoint:

* `websecure`

TLS:

* enabled

Traefik target port:

* `80`

Middleware:

* `${TRAEFIK_AUTH_MIDDLEWARE}`

No direct host HTTP port is published in this stack.

---

## Content Model

The stack serves a static site from files mounted into the Nginx web root:

* `site/index.html`
* `shared/service-catalog/`
* `site/timopoly-ui.css`

Current checked-in behavior:

* `index.html` fetches `/service-catalog/services.json`
* the page reads the generated shared service catalog schema
* service cards are rendered client-side in the browser
* search/filter behavior is implemented in the page script
* the landing page hides the `www.timopoly.com` self-entry from the generated catalog
* the footer shows the catalog `generated_at` timestamp when present
* the shared catalog directory mount allows atomic `services.json` rewrites to appear without recreating the `landing` container

The active runtime `services.json` is the generated shared service catalog artifact.

---

## Storage / Mounts

Read-only bind mounts:

* `/home/tim/stacks/apps/landing/site/index.html` -> `/usr/share/nginx/html/index.html`
* `/home/tim/stacks/shared/service-catalog` -> `/usr/share/nginx/html/service-catalog`
* `/home/tim/stacks/apps/landing/site/timopoly-ui.css` -> `/usr/share/nginx/html/timopoly-ui.css`

No named volumes are defined in the checked-in Compose file.

---

## Networks

Attached networks:

* external `proxy`

This stack does not define an internal network in the checked-in Compose file.

---

## Dependencies

No `depends_on` relationships are declared in the checked-in Compose file.

Infrastructure dependencies implied by the checked-in routing model:

* Traefik / gateway for HTTP(S) routing
* external `proxy` Docker network
* Cloudflare / cloudflared path for public exposure, as described by the repo ingress model

UI/data dependencies visible from checked-in files:

* `index.html` depends on `services.json`
* `index.html` depends on `timopoly-ui.css`

---

## Service Catalog Status

The repo contains service-catalog tooling and architecture documentation:

* `bin/generate-service-catalog`
* `docs/architecture/service-catalog.md`

Current checked-in landing stack status:

* this stack mounts `shared/service-catalog/`
* it reads the generated shared catalog artifact at `/service-catalog/services.json`
* the checked-in static `apps/landing/site/services.json` file is no longer the active runtime source

---

## UI Reuse

The stack includes a checked-in stylesheet reuse note:

* `apps/landing/README_UI_REUSE.txt`

That file documents reuse of:

* `site/timopoly-ui.css`
* `site/index.html`
* `site/services.json`

---

## Required Environment

The checked-in Compose file references:

* `TRAEFIK_AUTH_MIDDLEWARE`

No other environment variables are referenced directly in this stack’s `compose.yml`.

---

## Exposure Summary

Confirmed from the checked-in Compose file:

* public route on `www.timopoly.com`
* HTTPS entry via `websecure`
* Traefik auth middleware enabled
* no direct host HTTP port exposure

---

## Operations

Deploy or update:

```bash
stack up landing
```

Logs:

```bash
stack logs landing
```

Container status:

```bash
stack ps landing
```

---

## Unverified

The following are not documented here because they are not proven by the checked-in stack files alone:

* the exact Cloudflare DNS and tunnel ingress configuration for `www.timopoly.com`
* whether the landing page is intended to be publicly accessible without additional Cloudflare-side access controls
* whether the current service list should intentionally include `www.timopoly.com` as a visible card

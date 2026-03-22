# Authentik

## Purpose

This stack runs Authentik and its Traefik ForwardAuth outpost components.

Services defined in this stack:

* `authentik-server`
* `authentik-worker`
* `authentik-proxy`
* `authentik-postgres`
* `authentik-redis`

---

## Stack Class

Public app.

Reason:

* `authentik-server` is routed through Traefik on `Host(\`auth.${BASE_DOMAIN}\`)`
* `authentik-proxy` is also routed through Traefik for the outpost path on the same host
* both routed services join the external `proxy` network

---

## Routing

### Main Authentik UI / app

Routed service:

* `authentik-server`

Router rule:

* `Host(\`auth.${BASE_DOMAIN}\`)`

Entrypoint:

* `websecure`

TLS:

* enabled
* certresolver: `cloudflare`

Traefik target port:

* `9000`

### Authentik outpost path

Routed service:

* `authentik-proxy`

Router rule:

* `Host(\`auth.${BASE_DOMAIN}\`) && PathPrefix(\`/outpost.goauthentik.io/\`)`

Entrypoint:

* `websecure`

TLS:

* enabled

Priority:

* `200`

Traefik target port:

* `9000`

---

## Middleware

The checked-in Compose file does not apply `${TRAEFIK_AUTH_MIDDLEWARE}` to the Authentik routes.

Documented behavior from Compose comments:

* `authentik-server` explicitly notes that it must not be protected with Authentik ForwardAuth

No other middleware is defined on the Authentik routers in this stack.

---

## Dependencies

Service dependencies declared in Compose:

* `authentik-server` depends on `authentik-postgres` and `authentik-redis`
* `authentik-worker` depends on `authentik-postgres` and `authentik-redis`
* `authentik-proxy` depends on `authentik-server`

Internal service relationships configured through environment:

* PostgreSQL host: `authentik-postgres`
* Redis host: `authentik-redis`
* outpost internal Authentik host: `http://authentik-server:9000`

---

## Networks

Defined networks:

* `internal` bridge network
* external `proxy` network

Attached by service:

* `authentik-postgres`: `internal`
* `authentik-redis`: `internal`
* `authentik-server`: `internal`, `proxy`
* `authentik-worker`: `internal`
* `authentik-proxy`: `internal`, `proxy`

---

## Volumes

Named volumes:

* `authentik_pgdata` mounted at `/var/lib/postgresql/data`
* `authentik_media` mounted at `/media`

Used by:

* `authentik-postgres` -> `authentik_pgdata`
* `authentik-server` -> `authentik_media`
* `authentik-worker` -> `authentik_media`

---

## Required Environment

The checked-in Compose file requires these variables:

* `AUTHENTIK_POSTGRES_PASSWORD`
* `AUTHENTIK_SECRET_KEY`

The stack also references these non-secret variables:

* `BASE_DOMAIN`
* `AUTHENTIK_OUTPOST_TOKEN`

Notes:

* `AUTHENTIK_POSTGRES_PASSWORD` and `AUTHENTIK_SECRET_KEY` use fail-fast interpolation and are required
* `AUTHENTIK_OUTPOST_TOKEN` is optional in Compose because it uses `${AUTHENTIK_OUTPOST_TOKEN:-}`

---

## Images

Images used:

* `postgres:16-alpine`
* `redis:7-alpine`
* `ghcr.io/goauthentik/server:latest`
* `ghcr.io/goauthentik/proxy:latest`

---

## Operations

Deploy or update:

```bash
stack up authentik
```

Logs:

```bash
stack logs authentik
```

Container status:

```bash
stack ps authentik
```

---

## Unverified

The following are not documented here because they are not proven by the checked-in `compose.yml` alone:

* bootstrap or first-login procedure
* expected public exposure beyond the configured hostname/path rules
* exact Authentik application behavior after startup
* any required Cloudflare, DNS, or gateway-side configuration outside this stack

# Routing Contract

This document defines the routing rules for services in this repository.

It complements:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/runbooks/public-app-publish.md`
- `docs/runbooks/debug-traefik.md`

The goal is to make routing behavior deterministic for humans and AI agents.

---

## Purpose

Use this contract when:

- adding a new routed service
- changing a hostname
- modifying Traefik labels
- deciding whether a service is public, LAN-only, or internal-only
- debugging routing or middleware behavior

---

## Routing model

This repository uses Traefik as the single HTTP(S) entrypoint.

Typical paths:

### Public app path

Client -> Cloudflare DNS -> cloudflared -> Traefik -> middleware -> target service

### LAN-only app path

Client -> LAN DNS / local hostname -> Traefik -> middleware -> target service

### Internal-only path

No end-user route. Service is reachable only by other containers or explicitly documented admin tooling.

---

## Service classes

Every service must be classified before routing is added.

### 1. Public service

A public service is reachable from outside the LAN.

Requirements:

- routed through Traefik
- attached to `proxy`
- uses explicit `Host()` rule
- uses `websecure`
- uses TLS
- uses the intended certresolver
- uses the shared auth middleware unless explicitly exempted

### 2. LAN-only service

A LAN-only service is reachable only from the local network.

Requirements:

- routed through Traefik unless explicitly documented otherwise
- attached to `proxy` if Traefik-routed
- uses local hostname rules
- uses LAN-only middleware where required
- must not be silently promoted to public exposure

### 3. Internal-only service

An internal-only service has no user-facing route.

Requirements:

- no public router labels
- no accidental `proxy` attachment
- no direct host exposure unless explicitly documented

---

## Core routing rules

### Rule 1 — All web traffic goes through Traefik

Do not expose web apps directly with `ports:` when Traefik is the intended entrypoint.

### Rule 2 — Labels belong on the routed service

Traefik labels must be placed on the container that Traefik actually forwards requests to.

Usually this is:
- the frontend/UI container for a web app
- a single app container for a standalone service

Do not place public labels on unrelated backends.

### Rule 3 — Routed services must join `proxy`

Any service with active Traefik labels must:

- join the external `proxy` network
- set `traefik.docker.network=proxy`

### Rule 4 — Backends stay off `proxy` by default

A backend/internal service must not join `proxy` unless there is a verified reason.

### Rule 5 — Host rules must be explicit

Use explicit host-based routing.

Preferred form:

```yaml
traefik.http.routers.${APP_ID}.rule=Host(`${APP_HOST}.${BASE_DOMAIN}`)
```

Do not rely on vague or overly broad rules unless the service requires them and the reason is documented.

### Rule 6 — Public services use HTTPS

Public services must use:

- `entrypoints=websecure`
- `tls=true`
- the intended certificate resolver

### Rule 7 — Auth is handled by middleware

Protected services must use the shared authentication middleware through Traefik.

Do not implement ad hoc routing-time auth patterns when the shared middleware is the intended mechanism.

---

## Standard label patterns

### Public service pattern

```yaml
labels:
  - traefik.enable=true
  - traefik.docker.network=proxy
  - traefik.http.routers.${APP_ID}.rule=Host(`${APP_HOST}.${BASE_DOMAIN}`)
  - traefik.http.routers.${APP_ID}.entrypoints=websecure
  - traefik.http.routers.${APP_ID}.tls=true
  - traefik.http.routers.${APP_ID}.tls.certresolver=${TRAEFIK_CERTRESOLVER:-cloudflare}
  - traefik.http.routers.${APP_ID}.middlewares=${TRAEFIK_AUTH_MIDDLEWARE}
  - traefik.http.services.${APP_ID}.loadbalancer.server.port=80
```

### LAN-only service pattern

```yaml
labels:
  - traefik.enable=true
  - traefik.docker.network=proxy
  - traefik.http.routers.${APP_ID}.rule=Host(`${APP_HOST}.${LAN_DOMAIN}`)
  - traefik.http.routers.${APP_ID}.entrypoints=web
  - traefik.http.routers.${APP_ID}.middlewares=lan-only@file
  - traefik.http.services.${APP_ID}.loadbalancer.server.port=8080
```

These are defaults. A stack may intentionally vary, but any exception should be documented.

---

## Router naming contract

Router names should derive from `APP_ID`.

Preferred pattern:

- router name: `${APP_ID}`
- service name: `${APP_ID}`

Rules:

- avoid random router names unrelated to the stack
- avoid multiple routers for a simple stack unless needed
- if multiple routers exist, use clear suffixes

Examples:

- `${APP_ID}`
- `${APP_ID}-http`
- `${APP_ID}-https`
- `${APP_ID}-auth-callback`

---

## Hostname contract

### Public hostnames

Public hostnames should follow the stack’s public naming convention.

Preferred pattern:

- `${APP_HOST}.${BASE_DOMAIN}`

Rules:

- `APP_HOST` should be stable
- `APP_HOST` should match the intended Cloudflare hostname
- do not invent alternate hostnames unless documented

### LAN hostnames

LAN-only hostnames should follow the local naming convention.

Preferred pattern:

- `${APP_HOST}.${LAN_DOMAIN}`

Rules:

- do not point LAN-only services at public DNS unintentionally
- keep LAN naming consistent with local DNS policy

---

## Entrypoint contract

### Public services

Use:
- `websecure`

May also use an HTTP router only if the gateway intentionally performs redirect behavior and the pattern is already established.

### LAN-only services

Use:
- `web` or the repo’s LAN-specific entrypoint pattern, if defined

Do not assume LAN-only services need TLS unless the repo explicitly uses it for LAN routes.

---

## TLS contract

For public services:

- `tls=true` must be present
- the configured certresolver must exist
- the hostname must match DNS and tunnel configuration

Rules:

- do not add TLS labels to a public route without using the correct entrypoint
- do not assume the default resolver name without checking env/config
- do not use placeholder resolvers in committed config

---

## Middleware contract

### Shared auth middleware

Protected public services should use the shared auth middleware variable or the documented shared middleware chain.

Typical pattern:

```yaml
traefik.http.routers.${APP_ID}.middlewares=${TRAEFIK_AUTH_MIDDLEWARE}
```

### LAN-only middleware

LAN-only services should use the documented local-access middleware when appropriate.

Example:

```yaml
traefik.http.routers.${APP_ID}.middlewares=lan-only@file
```

### Middleware rules

- referenced middleware must exist
- provider suffix must be correct where required
- middleware order must be preserved when a chain is used
- do not mix public and LAN middleware patterns accidentally

---

## Authentik routing rules

Authentik has special routing constraints.

Rules:

- Authentik itself must not be protected by its own ForwardAuth middleware
- outpost/proxy endpoints must route correctly
- HTTPS must be working before auth handoff for public services
- do not apply the shared auth middleware to Authentik unless explicitly documented for a special path

Common failure symptom:
- login loops or immediate auth failure caused by wrong middleware placement

---

## Backend routing rules

Internal backends:

- should not carry Traefik labels
- should not be publicly routable by default
- should not be attached to `proxy` without verified need

If a backend must be directly routed:
- document why
- keep routing scoped to that service only

---

## Direct port exposure rules

Avoid `ports:` for Traefik-routed HTTP services.

Allowed only when:
- the service is intentionally non-Traefik
- the service uses a non-HTTP protocol that requires host exposure
- the reason is documented

Never use direct host ports as a shortcut to avoid fixing Traefik.

---

## Validation checklist

A routed service is valid only when:

- the correct service has the labels
- the routed service is on `proxy`
- `traefik.docker.network=proxy` is set
- the hostname matches the intended route
- the service port matches the real in-container listening port
- middleware references exist
- public routes use TLS and correct entrypoints
- internal-only services have no accidental public routing

---

## Common mistakes

### Labels on the wrong service

Symptom:
- route exists but points nowhere useful
- router loads but upstream behavior is wrong

Fix:
- move labels to the real route target

### Service missing `proxy`

Symptom:
- route may load but upstream fails
- Traefik cannot reach the container correctly

Fix:
- attach routed service to `proxy`
- set `traefik.docker.network=proxy`

### Wrong load balancer port

Symptom:
- 502 / 504 from Traefik

Fix:
- verify actual in-container listening port
- update `loadbalancer.server.port`

### Wrong hostname rule

Symptom:
- 404 through Traefik

Fix:
- verify exact `Host()` rule
- verify requested hostname matches DNS/tunnel config

### Wrong middleware

Symptom:
- login loop
- unexpected access behavior
- middleware not found

Fix:
- verify middleware name
- verify provider suffix
- verify service class and expected chain

### LAN service accidentally made public

Symptom:
- local service appears on public edge path

Fix:
- remove public hostname/routing
- restore LAN-only hostname and middleware
- verify Cloudflare/tunnel config is not pointing at it

---

## Debug order

When routing fails, use this order:

1. verify service is running
2. verify the correct service carries labels
3. verify `proxy` attachment
4. verify hostname rule
5. verify target port
6. verify middleware
7. verify Traefik logs
8. verify DNS / tunnel edge path

See `docs/runbooks/debug-traefik.md` for the detailed procedure.

---

## Exceptions

A routing exception is allowed only when:

- there is a real technical reason
- the reason is documented
- the exception does not silently weaken the overall security model

Examples:
- a service requires separate auth callback router
- a service requires additional router rules for a documented path
- a service intentionally exposes a non-HTTP port outside Traefik

---

## Definition of done

A routing change is complete when:

- the service class is correct
- the hostname is correct
- the labels are on the correct service
- the route works through the intended entrypoint
- required middleware loads successfully
- no unintended exposure was introduced

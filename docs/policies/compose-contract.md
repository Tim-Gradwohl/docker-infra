# Compose Contract

This document defines the required Compose patterns for stacks in this repository.

It is the implementation companion to `AGENTS.md`. Where `AGENTS.md` defines agent behavior and policy, this file defines what a valid stack should look like.

---

## Purpose

Use this contract when:

- creating a new stack
- reviewing an existing stack
- deciding whether a stack is public, LAN-only, or internal-only
- validating whether a Compose file matches repo standards

If a stack intentionally deviates from this contract, document the exception in that stack’s README.

---

## Stack classes

Every stack must be classified as one of the following:

### 1. Public app

A public app is reachable from outside the LAN through the normal edge path:

Cloudflare DNS / Tunnel -> Traefik -> Authentik (if protected) -> app

Requirements:

- routed through Traefik
- routed service joins `proxy`
- uses explicit host-based Traefik labels
- uses HTTPS on `websecure`
- uses the shared auth middleware unless explicitly exempted
- does not expose its own HTTP port directly

### 2. LAN-only app

A LAN-only app is reachable only on the local network.

Requirements:

- routed through Traefik or explicitly documented otherwise
- not added to public Cloudflare DNS or public tunnel ingress by default
- uses LAN-specific routing and middleware where applicable
- does not silently become a public app

### 3. Internal-only service

An internal-only service is not directly user-facing.

Requirements:

- no public host routing
- no direct public exposure
- no Traefik labels unless there is a verified reason
- only minimum required networks are attached

---

## Required Compose structure

### Project naming

Prefer:

```yaml
name: ${APP_ID}
```

Rules:

- `APP_ID` must be stable and filesystem-safe
- service/router naming should derive from `APP_ID`
- avoid hardcoded duplicate identifiers when variables are already available

### Service layout

Prefer separating services by role:

- frontend / UI service
- backend / API service
- database / cache / worker services

Rules:

- only the service Traefik actually targets should carry public routing labels
- backend services should not carry Traefik labels unless they are intentionally routed
- backend services should not join `proxy` by default

### Restart policy

Prefer:

```yaml
restart: unless-stopped
```

Use a different restart policy only if the stack has a documented reason.

---

## Network contract

### Internal network

Use an internal bridge network for service-to-service traffic.

Preferred pattern:

```yaml
networks:
  internal:
    driver: bridge
```

Attach backend components to `internal` unless there is a verified need for additional networks.

### Proxy network

Use the shared external `proxy` network for Traefik-routed services.

Preferred pattern:

```yaml
networks:
  proxy:
    external: true
```

Rules:

- only routed services should join `proxy`
- if a service has Traefik labels, it must be on `proxy`
- set `traefik.docker.network=proxy` on routed services
- do not attach all services to `proxy` by habit

### Ports

Rules:

- do not expose HTTP(S) ports directly for Traefik-routed apps
- do not expose databases externally
- avoid `ports:` unless the service is intentionally non-Traefik and the reason is explicit
- if `ports:` is required, document why

---

## Routing contract

### Routed service labels

A routed service must define all labels needed for Traefik to discover and route to it.

Preferred public pattern:

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

Rules:

- host rules must be explicit
- router names should derive from `APP_ID`
- service names should derive from `APP_ID`
- the service port must match the actual in-container listening port
- labels belong on the routed service, not on unrelated backends

### Public routing

Public apps must:

- use `websecure`
- enable TLS
- use the intended certificate resolver
- follow the repo’s public edge path

### LAN-only routing

LAN-only apps should use:

- local hostname rules
- LAN-specific middleware where appropriate
- no public DNS/tunnel assumptions unless explicitly documented

### Auth middleware

Rules:

- use the shared auth middleware for protected public apps
- do not apply the auth middleware to Authentik itself
- preserve middleware ordering requirements where a chain is used

---

## Environment contract

### Required env usage

Prefer variables over hardcoded identifiers.

Typical values include:

- `APP_ID`
- `APP_HOST`
- `BASE_DOMAIN`
- `TZ`
- `TRAEFIK_CERTRESOLVER`
- `TRAEFIK_AUTH_MIDDLEWARE`

Rules:

- use `shared/.env.global` for shared, non-secret values
- use `shared/.env.secrets` for secrets
- never hardcode secrets into Compose files
- use fail-fast interpolation for required values when appropriate

Preferred required variable example:

```yaml
environment:
  SOME_REQUIRED_VALUE: ${SOME_REQUIRED_VALUE:?SOME_REQUIRED_VALUE is required}
```

### .env files

Each stack may define a local `.env` for stack-specific values, but shared values must not be duplicated unnecessarily.

Rules:

- stack-local `.env` should contain only stack-specific values
- shared values belong in shared env contracts
- examples should be provided when setup requires local values

---

## Volumes and storage contract

Rules:

- use explicit bind mounts or named volumes
- avoid unexplained host path sprawl
- mount only what the service requires
- writable mounts should be minimized
- document any unusual storage layout in the stack README

Preferred bind syntax:

```yaml
volumes:
  - ./data:/data:rw
```

For stateful services:

- clearly separate config, data, and media where possible
- do not mount broad host paths without reason

---

## Security contract

Apply least privilege where compatible.

Preferred defaults:

```yaml
security_opt:
  - no-new-privileges:true
```

Use additional hardening where supported:

- `read_only: true`
- `cap_drop`
- explicit non-root user
- `tmpfs` for ephemeral writable paths

Rules:

- do not use `privileged: true` unless the service truly requires it
- if elevated privileges are required, document why
- do not mount the Docker socket unless the service explicitly requires Docker control
- Docker socket access is high-trust and must be justified

---

## Health and startup contract

### Healthchecks

Add healthchecks where they provide meaningful signal.

Preferred pattern:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q -O - http://127.0.0.1/ >/dev/null 2>&1 || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 15s
```

Rules:

- healthchecks should test real service readiness when practical
- filesystem-only checks are acceptable only when better probes are unavailable
- healthchecks should not be intentionally noisy or expensive

### depends_on

Rules:

- `depends_on` controls startup ordering, not full readiness
- do not treat `depends_on` as proof that a dependency is healthy
- if dependency readiness matters, prefer healthchecks and document the real dependency expectations

---

## GPU contract

If a service needs GPU access, make it explicit on only that service.

Example:

```yaml
gpus: all
```

Rules:

- do not add GPU access to services that do not need it
- keep GPU workloads isolated to the minimum necessary container set

---

## Template patterns

### Public web app template

```yaml
name: ${APP_ID}

services:
  ui:
    build:
      context: .
      dockerfile: ./docker/nginx/Dockerfile
    restart: unless-stopped
    depends_on:
      api:
        condition: service_started
    networks:
      - internal
      - proxy
    security_opt:
      - no-new-privileges:true
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.${APP_ID}.rule=Host(`${APP_HOST}.${BASE_DOMAIN}`)
      - traefik.http.routers.${APP_ID}.entrypoints=websecure
      - traefik.http.routers.${APP_ID}.tls=true
      - traefik.http.routers.${APP_ID}.tls.certresolver=${TRAEFIK_CERTRESOLVER:-cloudflare}
      - traefik.http.routers.${APP_ID}.middlewares=${TRAEFIK_AUTH_MIDDLEWARE:?TRAEFIK_AUTH_MIDDLEWARE is required}
      - traefik.http.services.${APP_ID}.loadbalancer.server.port=80

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      TZ: ${TZ:-Europe/Berlin}
    networks:
      - internal
    security_opt:
      - no-new-privileges:true

networks:
  internal:
    driver: bridge
  proxy:
    external: true
```

### LAN-only app template

```yaml
name: ${APP_ID}

services:
  app:
    image: your-image:tag
    restart: unless-stopped
    networks:
      - proxy
    security_opt:
      - no-new-privileges:true
    labels:
      - traefik.enable=true
      - traefik.docker.network=proxy
      - traefik.http.routers.${APP_ID}.rule=Host(`${APP_HOST}.${LAN_DOMAIN}`)
      - traefik.http.routers.${APP_ID}.entrypoints=web
      - traefik.http.routers.${APP_ID}.middlewares=lan-only@file
      - traefik.http.services.${APP_ID}.loadbalancer.server.port=8080

networks:
  proxy:
    external: true
```

### Internal-only service template

```yaml
name: ${APP_ID}

services:
  worker:
    image: your-image:tag
    restart: unless-stopped
    networks:
      - internal
    security_opt:
      - no-new-privileges:true

networks:
  internal:
    driver: bridge
```

---

## Validation checklist

A stack is not considered complete until the following are true.

### Compose validation

- Compose renders correctly
- variable names are consistent
- required variables are documented
- networks are intentional
- no unnecessary `proxy` attachments exist

### Exposure validation

For public apps:

- service is attached to `proxy`
- Traefik labels match intended host
- TLS configuration is present
- auth middleware is correct
- no direct `ports:` bypass exists

For LAN-only apps:

- no unintended public exposure exists
- local routing is correct
- middleware matches local-access policy

For internal-only services:

- no Traefik labels exist unless justified
- no public ports are published

### Security validation

- no secrets are hardcoded
- privilege level is justified
- Docker socket usage is justified
- writable mounts are limited to what is required

### Documentation validation

- stack README documents any exceptions
- examples match actual Compose structure
- docs do not claim behavior not present in checked-in files

---

## Exceptions

Intentional deviations are allowed only when:

- there is a real technical requirement
- the deviation is minimal
- the reason is documented in the stack README or relevant runbook

Examples of acceptable exceptions:

- direct port exposure for a non-HTTP protocol
- Docker socket access for a tooling container that genuinely requires it
- elevated privileges for a service with explicit platform requirements

---

## Definition of done

A Compose change is complete when:

- it matches the correct stack class
- it follows the network and routing contract
- env usage is consistent with repo policy
- security posture is reasonable for the service
- docs reflect the actual checked-in behavior
- no broader repo pattern was broken to solve a local problem

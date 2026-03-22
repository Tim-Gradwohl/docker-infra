# Gitea

## Purpose

This stack runs the Gitea web application for Git over HTTP(S).

Operator note provided in-session:

* Gitea is the main private source of truth
* changes are pushed to private Gitea first
* the private Gitea then mirrors to the public GitHub repository

The routing and runtime details below are based on the checked-in `compose.yml`.

---

## Stack Class

Public app.

Reason:

* the stack is routed through Traefik
* the router rule is `Host(\`gitea.${BASE_DOMAIN}\`)`
* the routed service joins the external `proxy` network
* the route uses `websecure` with TLS enabled

---

## Main Service

Service:

* `gitea`

Image:

* `gitea/gitea:latest`

Restart policy:

* `unless-stopped`

Container name:

* `gitea`

---

## Routing

Routed service:

* `gitea`

Router rule:

* `Host(\`gitea.${BASE_DOMAIN}\`)`

Entrypoint:

* `websecure`

TLS:

* enabled
* certresolver: `cloudflare`

Traefik service target:

* service name: `gitea`
* container port: `3000`

No direct host HTTP port is published in this stack.

---

## Middleware

The checked-in Compose file does not currently apply `${TRAEFIK_AUTH_MIDDLEWARE}` to the Gitea router.

The file contains commented middleware examples only:

* `${TRAEFIK_AUTH_MIDDLEWARE}`
* `lan-allowlist@file,auth-basic@file`

As checked in, the route has no active Traefik middleware configured in this stack.

---

## Environment

The checked-in Compose file sets:

* `USER_UID=1000`
* `USER_GID=1000`
* `GITEA__server__DOMAIN=gitea.${BASE_DOMAIN}`
* `GITEA__server__ROOT_URL=http://gitea.${BASE_DOMAIN}/`
* `GITEA__server__HTTP_PORT=3000`
* `GITEA__server__START_SSH_SERVER=false`

Variables referenced from repo/global context:

* `BASE_DOMAIN`

Notes from checked-in config:

* SSH server is disabled
* the stack is configured for HTTP(S) Git only
* registration hardening is present only as a commented optional setting

---

## Storage

Volumes:

* named volume `gitea_data` mounted at `/data`
* `/etc/timezone:/etc/timezone:ro`
* `/etc/localtime:/etc/localtime:ro`

---

## Networks

Attached networks:

* external `proxy`

This stack does not define an internal network in the checked-in Compose file.

---

## Dependencies

No `depends_on` relationships are declared in the checked-in Compose file.

Infrastructure dependencies implied by routing:

* Traefik / gateway for HTTP(S) routing
* the external `proxy` Docker network

---

## Exposure Summary

Confirmed from the checked-in Compose file:

* public Traefik route on `gitea.${BASE_DOMAIN}`
* HTTPS/TLS enabled on `websecure`
* no direct host HTTP port exposure
* no Traefik auth middleware currently enabled in this stack

---

## Operations

Deploy or update:

```bash
stack up gitea
```

Logs:

```bash
stack logs gitea
```

Container status:

```bash
stack ps gitea
```

---

## Unverified

The following are not documented here because they are not proven by the checked-in `compose.yml` alone:

* repository mirroring configuration details inside Gitea
* user, org, and permission model
* webhook behavior
* backup procedure
* whether the configured `ROOT_URL` is intentionally HTTP behind Traefik or should be changed

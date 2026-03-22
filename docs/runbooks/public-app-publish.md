# Public App Publish Runbook

This runbook defines the **standard procedure to publish a new public app** in this repository.

It follows:
- `AGENTS.md` (policy & constraints)
- `docs/policies/compose-contract.md` (Compose contract)

---

## Purpose

Use this runbook when:

- adding a new internet-facing service
- exposing an existing LAN/internal service publicly
- fixing a broken public route

---

## Definition of a Public App

A public app is reachable via:

Cloudflare → Tunnel → Traefik → Authentik → Service

It must:
- be reachable via public DNS
- be routed through Traefik
- use HTTPS
- optionally be protected by Authentik

---

## Preconditions

Before starting, verify:

- domain exists in Cloudflare
- tunnel is configured and running (`cloudflared`)
- Traefik is running and connected to `proxy`
- Authentik is operational (if auth is required)

If any of these are missing → STOP and fix infrastructure first.

---

## Step 1 — Create Stack

Create new directory:

```
apps/<app-name>/
```

Add:
- `compose.yml`
- `.env` (if needed)
- `README.md`

Use the **public app template** from `compose-contract.md`.

---

## Step 2 — Configure Environment

Define required variables:

```
APP_ID=<app_id>
APP_HOST=<subdomain>
```

Ensure global values exist:

- `BASE_DOMAIN`
- `TRAEFIK_AUTH_MIDDLEWARE`
- `TRAEFIK_CERTRESOLVER`

Do NOT hardcode secrets.

---

## Step 3 — Configure Traefik Routing

Verify labels on routed service:

- `traefik.enable=true`
- `traefik.docker.network=proxy`
- correct `Host()` rule
- `entrypoints=websecure`
- `tls=true`
- correct certresolver
- auth middleware (if required)

Ensure:
- service is attached to `proxy`
- no direct `ports:` exposure

---

## Step 4 — Deploy Stack

```
stack up <app>
```

Verify:
- containers start
- no immediate crashes

---

## Step 5 — Verify Container State

```
stack ps <app>
```

Check:
- all services are running
- no restart loops

---

## Step 6 — Verify Networking

Ensure routed container:

- is attached to `proxy`
- is attached to `internal` if needed

---

## Step 7 — Verify Traefik Routing

Check:

- route appears in Traefik dashboard/logs
- no middleware errors
- correct service port is used

Common issues:
- wrong network
- wrong label names
- missing middleware

---

## Step 8 — Verify DNS and Tunnel

Check:

- DNS record exists in Cloudflare
- tunnel routes hostname to Traefik

If DNS works but service does not:
→ problem is inside Docker / Traefik

---

## Step 9 — Verify Access

Open:

```
https://<APP_HOST>.<BASE_DOMAIN>
```

Check:

- HTTPS works
- certificate is valid
- page loads

If protected:

- Authentik login appears
- login succeeds
- redirect works

---

## Step 10 — Validate Security

Confirm:

- no unintended ports exposed
- service not publicly reachable outside Traefik
- auth middleware applied (if required)

---

## Step 11 — Documentation

Update:

- `apps/<app>/README.md`
- any relevant docs

Document:
- purpose
- ports (internal)
- volumes
- special requirements
- exceptions to policy

---

## Troubleshooting

### 404 from Traefik

Check:
- container running
- container on `proxy`
- labels correct

---

### Auth loop / failure

Check:
- HTTPS enforced
- middleware correct
- Authentik reachable

---

### Service unreachable

Check:
- container logs
- internal port matches label
- service actually listening

---

### Works locally but not externally

Check:
- DNS
- Cloudflare tunnel
- hostname mismatch

---

## Rollback

If deployment breaks:

```
stack down <app>
```

Revert changes in Git.

---

## Definition of Done

A public app is complete when:

- reachable via HTTPS
- correctly routed via Traefik
- auth works (if enabled)
- no direct port exposure
- follows compose contract
- documentation is updated

---

## Notes

- Do not bypass Traefik
- Do not expose services directly
- Do not skip validation steps

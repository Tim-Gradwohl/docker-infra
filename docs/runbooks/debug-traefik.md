# Traefik Debug Runbook

This runbook defines the standard procedure for debugging Traefik-related routing problems in this repository.

It follows:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/runbooks/public-app-publish.md`

---

## Purpose

Use this runbook when:

- a service returns 404 through Traefik
- a route is missing
- TLS is failing
- middleware is not applied correctly
- Authentik integration appears broken
- a service works internally but not through its hostname

---

## Scope

This runbook is for issues in the path:

Client -> Cloudflare -> cloudflared -> Traefik -> middleware -> target service

It is not the primary runbook for:
- app-specific crashes
- database failures
- VPN-only failures unrelated to Traefik
- LAN DNS issues unrelated to Traefik routing

---

## Quick triage

Before deep debugging, classify the failure.

### 1. 404 from Traefik

Likely causes:
- route not discovered
- service not on `proxy`
- labels missing or malformed
- hostname rule mismatch
- wrong router/service name

### 2. 502 / 504 from Traefik

Likely causes:
- target container is down
- target port is wrong
- target service is listening on a different port/interface
- upstream is unhealthy or timing out

### 3. TLS / certificate issue

Likely causes:
- router not on `websecure`
- TLS not enabled
- wrong or missing certresolver
- hostname not matching expected domain
- Cloudflare/tunnel host mismatch

### 4. Auth loop / auth failure

Likely causes:
- wrong middleware
- middleware ordering problem
- Authentik route broken
- HTTPS not enforced before auth
- outpost route unavailable

---

## Standard debug order

Always use this order unless there is a documented exception:

1. verify the target service is running
2. verify network attachment
3. verify Traefik labels
4. verify Traefik router/service configuration
5. check Traefik logs
6. verify middleware
7. verify Cloudflare / tunnel edge path
8. verify app-level listening port and readiness

Do not skip straight to DNS or certificates before confirming local Docker routing is correct.

---

## Step 1 — Verify container state

Check whether the target stack is actually running.

```bash
stack ps <stack>
```

Look for:
- service is up
- no crash loops
- expected frontend container exists
- expected backend container exists

If the target container is not running, fix that first.
Traefik cannot route to a container that is down.

---

## Step 2 — Verify the route target

Identify which service Traefik is supposed to route to.

Rules:
- Traefik labels belong on the actual routed service
- usually this is the frontend/UI container
- backend-only services should not be the public route target unless explicitly intended

Common mistake:
- labels placed on backend service while Traefik should route to frontend
- labels placed on multiple services unnecessarily

---

## Step 3 — Verify network attachment

For any Traefik-routed service, verify:

- target service is attached to `proxy`
- label includes `traefik.docker.network=proxy`

If a service has routing labels but is not on `proxy`, Traefik may discover the router but fail to reach the container correctly.

Common mistake:
- service has labels but only joins `internal`
- backend service joins `proxy` unnecessarily while frontend does not

---

## Step 4 — Verify labels

Check the routed service’s labels carefully.

Expected public pattern typically includes:

- `traefik.enable=true`
- `traefik.docker.network=proxy`
- `traefik.http.routers.<router>.rule=Host(...)`
- `traefik.http.routers.<router>.entrypoints=websecure`
- `traefik.http.routers.<router>.tls=true`
- `traefik.http.routers.<router>.tls.certresolver=...`
- `traefik.http.routers.<router>.middlewares=...`
- `traefik.http.services.<service>.loadbalancer.server.port=<port>`

Validate:

- router name is consistent
- service name is consistent
- hostname is correct
- target port matches the app’s in-container listening port
- labels are attached to the correct container

Common label errors:
- typo in router name
- typo in middleware reference
- typo in service name
- wrong `Host()` value
- wrong load balancer port
- missing backticks or malformed rule syntax

---

## Step 5 — Verify app listening port

A frequent cause of 502 is a mismatch between the Traefik service port label and the actual in-container port.

Example:
- Traefik label points to port `80`
- app actually listens on `3000`

Check:
- application config
- Dockerfile / container defaults
- stack README if available

Do not assume the internal port from image conventions.
Verify it from checked-in config.

---

## Step 6 — Check Traefik logs

Inspect Traefik logs for:

- router parse errors
- middleware not found
- service not found
- provider errors
- TLS resolver issues
- upstream connection failures

Use:

```bash
stack logs traefik
```

Or the equivalent gateway stack name used in this repo.

Look for messages indicating:
- configuration rejected
- router created but upstream unavailable
- middleware chain reference invalid
- certificate resolution failure

---

## Step 7 — Distinguish 404 vs upstream failure

This distinction matters.

### If you get 404

Usually means:
- Traefik did not match the route
- hostname rule is wrong
- request reached Traefik but no router matched
- wrong entrypoint or router not loaded

Focus on:
- host rule
- router labels
- entrypoint labels
- hostname being requested

### If you get 502/504

Usually means:
- router matched
- Traefik tried to forward
- upstream service or port is broken

Focus on:
- service health
- target port
- network reachability
- app readiness

---

## Step 8 — Verify middleware chain

If the route exists but behavior is wrong, inspect middleware.

Common middleware issues:
- referenced middleware does not exist
- wrong provider suffix
- wrong order in chain
- auth middleware applied where it should not be
- LAN-only middleware used on a public app
- Authentik middleware applied to Authentik itself

Rules:
- protected public apps should use the shared auth middleware
- Authentik itself must not be protected by its own ForwardAuth middleware
- middleware names should match checked-in dynamic config

If middleware is unclear, inspect:
- `gateway/`
- dynamic config files
- shared middleware definitions

---

## Step 9 — Verify HTTPS and TLS settings

For public apps, verify:

- router uses `websecure`
- `tls=true` is present
- certresolver is correct
- requested hostname matches expected public hostname

Common issues:
- app bound only to `web`
- TLS configured on wrong router
- hostname differs from DNS/tunnel configuration
- certresolver name does not exist

If the app redirects strangely during login, verify HTTPS is enforced before auth flow.

---

## Step 10 — Verify Authentik path

When auth is involved, check:

- Authentik itself is up
- outpost route exists
- middleware reference is valid
- headers/middleware chain are intact
- HTTPS is working before auth handoff

Symptoms of auth path issues:
- infinite redirect loop
- immediate 401/403
- login page never appears
- callback fails after login

Do not debug application auth first if the Traefik ForwardAuth path is already broken.

---

## Step 11 — Verify Cloudflare and tunnel edge path

After local Docker/Traefik validation is correct, verify edge routing.

Check:
- public DNS record exists
- tunnel ingress points to Traefik
- hostname used in browser matches router rule
- Cloudflare hostname matches expected app host

If local routing is correct but external access fails, the issue is likely:
- DNS mismatch
- tunnel ingress mismatch
- Cloudflare configuration mismatch

Do not blame Traefik until local routing is proven correct.

---

## Step 12 — Check dynamic config dependencies

Some routes depend on shared middleware or dynamic config entries.

Verify:
- referenced middleware exists
- file provider config is valid
- no stale or renamed middleware references remain
- router references correct provider suffix, if required

Examples of failure patterns:
- `middleware not found`
- router loads but chain is incomplete
- auth chain references missing outpost middleware

---

## Common failure patterns

### Pattern: service returns 404 only on public hostname

Check:
- `Host()` rule matches exactly
- request hits the same hostname defined in labels
- router uses correct entrypoint
- Cloudflare/tunnel hostname is the same as router hostname

### Pattern: service works on container IP but not through Traefik

Check:
- service is on `proxy`
- Traefik service port label is correct
- middleware is not blocking
- router/service labels are on correct container

### Pattern: route exists but login loops forever

Check:
- HTTPS enforced before auth
- auth middleware is correct
- Authentik itself is not protected by its own middleware
- callback/outpost routes are working

### Pattern: route started failing after refactor

Check:
- renamed router/service labels
- changed middleware names
- moved labels to wrong service
- removed `proxy` network
- changed internal listening port without updating labels

---

## Minimal verification checklist

A Traefik-routed app is considered valid when:

- target container is running
- routed container is on `proxy`
- Traefik labels are syntactically correct
- requested hostname matches router rule
- target port matches real app port
- middleware references exist
- TLS settings are correct for public routes
- app responds successfully through its intended hostname

---

## Escalation

If the problem remains unresolved, gather:

- stack name
- target hostname
- routed service name
- relevant compose labels
- `stack ps <stack>` output
- `stack logs <stack>` output
- `stack logs traefik` output
- any dynamic middleware references involved

Then inspect the exact files involved:

- `apps/<stack>/compose.yml`
- `apps/<stack>/README.md`
- `gateway/` dynamic config
- relevant shared env files if hostnames or middleware names are variable-based

---

## Do not

- do not expose ports directly to bypass Traefik
- do not move labels around blindly
- do not assume 404 and 502 mean the same thing
- do not debug Cloudflare first when the local route is already broken
- do not apply auth middleware to Authentik itself
- do not assume the app listens on port 80 without verification

---

## Definition of done

A Traefik issue is resolved when:

- the correct hostname matches a loaded router
- the router forwards to the correct container and port
- required middleware loads successfully
- TLS/auth behavior matches the intended service class
- the app responds through its intended route without bypasses

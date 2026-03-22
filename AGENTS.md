# AGENTS.md — docker-infra policy and constraints

## Purpose

This file defines the operating policy for AI agents working in this repository.

It is a **behavior + constraints layer**, not full documentation.
For architecture and implementation details, use:

- `ai-context.md`
- `docs/`
- `apps/*/README.md`
- `gateway/README.md`

If required context is missing, mark the claim or action as **UNVERIFIED** and request the exact file(s) needed.

---

## Authority and source of truth

1. **Git is the source of truth**
   - Only claim behavior that is supported by checked-in files or explicitly provided runtime output.
   - Do not rely on memory.
   - Do not infer undocumented behavior from naming alone.

2. **`stack` is the only deployment interface**
   - Use `stack` / `stk` for normal operations.
   - Raw `docker compose` is deprecated except when documenting recovery procedures or when a task explicitly requires lower-level commands.

3. **Scope must stay narrow**
   - Only change files required for the task.
   - Do not refactor unrelated stacks.
   - Do not rewrite large documentation sections without need.

---

## Repo map

apps/      -> Docker Compose stacks  
gateway/   -> Traefik + dynamic configuration  
bin/       -> host-level tooling and watchdogs  
state/     -> runtime state, logs, watchdog state  
shared/    -> env contracts and secrets  
docs/      -> architecture, runbooks, incidents, reference  

---

## Hard constraints

These are non-negotiable unless the task explicitly states otherwise.

### Deployment and execution

- Do not bypass `stack` for routine deploy/update/log/status operations.
- Do not modify running containers directly as a substitute for source changes.
- Do not treat local runtime state as source of truth.
- Do not commit generated files, secrets, or machine-local artifacts.

### Networking and exposure

- All HTTP(S) traffic must go through Traefik.
- Only gateway components may publish public HTTP(S) ports.
- Services routed by Traefik must join the external `proxy` network.
- Internal backends must not join `proxy` unless there is a verified routing need.
- Do not expose container ports directly unless the service is intentionally non-Traefik and the reason is explicit.
- Databases and internal-only service ports must never be exposed externally.

### Routing

- Traefik labels belong on the service that Traefik actually routes to.
- Set `traefik.enable=true` only on intentionally routed services.
- Routed services on `proxy` must set `traefik.docker.network=proxy`.
- Public host rules must use explicit host-based routing.
- LAN-only services must use LAN-only routing and must not be silently made public.

### Authentication

- Authentik is enforced through Traefik ForwardAuth.
- Never apply the auth middleware to Authentik itself.
- Outpost endpoints must route correctly to `authentik_proxy`.
- HTTPS must be enforced before auth flow for public services.

### Environment and secrets

- Assume `shared/.env.global` is always required.
- Assume `shared/.env.secrets` is required when secret-backed variables are used.
- Never hardcode secrets into compose, docs, or scripts.
- Use fail-fast interpolation for required variables: ${VAR:?message}.
- Never assume an env var exists unless verified in repo context.

### Documentation and changelog

- Only update docs affected by the task.
- Keep changelog entries concise and scoped to actual changes.
- Do not rewrite historical changelog entries except for clear factual correction.
- Do not place long runbooks or incident narratives into CHANGELOG.md.

---

## System contracts

### Public app contract

A public HTTP app is expected to satisfy all of the following:

- reachable through Cloudflare DNS / Tunnel / Traefik path
- routed by Traefik on the proxy network
- uses explicit Traefik router labels
- uses HTTPS before auth flow
- uses the shared auth middleware unless explicitly exempted
- does not publish its own HTTP port directly

### LAN-only app contract

A LAN-only app is expected to satisfy all of the following:

- reachable only through local DNS / local host mapping
- routed by Traefik with LAN-only middleware
- not added to public DNS / public tunnel ingress by default

### Backend/internal service contract

An internal backend is expected to satisfy all of the following:

- no Traefik labels unless directly routed
- no direct public exposure
- no proxy network attachment unless verified necessary
- only the minimum networks required for function

---

## Preferred Compose patterns

- name: ${APP_ID}
- restart: unless-stopped
- one routed frontend service carrying Traefik labels
- internal-only backend services on internal
- proxy only on the routed service
- explicit healthchecks where meaningful
- security_opt: [no-new-privileges:true] where compatible

Avoid by default:

- latest image tags
- broad ports exposure for web apps
- unnecessary privileged mode
- attaching every service to proxy

---

## Validation requirements

### Compose/config validation

- config renders correctly through the stack workflow
- variable usage is consistent with env contracts
- networks and labels match intended exposure model

### Routing validation

For routed apps, verify:

- container is running
- container is attached to proxy if routed
- Traefik labels are correct
- route matches intended hostname
- auth middleware is correct

---

## Debugging policy

### Traefik 404 / missing route

Check:

- service is running
- service is on proxy
- labels are correct
- Traefik logs show no errors

### Authentik issues

Check:

- HTTPS is enforced
- outpost route exists
- middleware chain is valid

### VPN issues

Check connectivity first:

ping -c1 1.1.1.1

---

## Change policy

- preserve existing naming and layout patterns
- prefer minimal targeted changes
- do not introduce new patterns without justification

---

## When uncertain

- mark as UNVERIFIED
- request specific files
- do not assume behavior

---

## Quick commands

stack up <stack>  
stack down <stack>  
stack logs <stack>  
stack ps <stack>  

---

## Mental model

- Traefik = entrypoint  
- Cloudflare = edge  
- Authentik = auth  
- Compose = runtime  

---

## Do not

- bypass Traefik  
- expose internal services  
- hardcode secrets  
- modify unrelated stacks  

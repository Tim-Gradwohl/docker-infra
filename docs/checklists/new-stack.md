# New Stack Checklist

Use this checklist when creating a new stack in this repository.

This checklist complements:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/policies/routing-contract.md`
- `docs/policies/env-contract.md`

---

## Goal

A new stack is considered valid only when:

- its service class is explicit
- its Compose file follows repo contracts
- its env usage is scoped correctly
- its routing model is correct
- its documentation is complete
- no unnecessary exposure or privilege was introduced

---

## 1. Classify the stack

Before writing Compose, choose exactly one class:

- public app
- LAN-only app
- internal-only service

Do not start from labels or ports first.
The stack class determines the routing, middleware, and exposure model.

### Public app

Use when the service must be reachable from the public internet through:

Cloudflare -> cloudflared -> Traefik -> middleware -> service

### LAN-only app

Use when the service must be reachable only from the local network.

### Internal-only service

Use when the service should not be directly user-facing.

---

## 2. Create the stack directory

Create:

```text
apps/<stack>/
```

Expected minimum files:

- `compose.yml`
- `README.md`

For public stacks, also create:

- `service.meta.json`

Add a local `.env` only if the stack truly has stack-specific variables.

---

## 3. Choose the correct template

Use the correct template from `docs/policies/compose-contract.md`.

- public app template
- LAN-only template
- internal-only template

Do not start from a random existing stack unless it is a known-good reference for the same class.

---

## 4. Set stack identity

Define stable identity values.

Typical local values:

```dotenv
APP_ID=myapp
APP_HOST=myapp
```

Rules:

- `APP_ID` should be stable and filesystem-safe
- `APP_HOST` should match the intended hostname
- do not invent alternate naming patterns without reason

---

## 5. Decide env scope

For every variable, decide whether it is:

- shared non-secret
- shared secret
- stack-local

Put variables in the correct place:

- `shared/.env.global`
- `shared/.env.secrets`
- `apps/<stack>/.env`

Do not duplicate shared values into the stack-local `.env` unless there is a true local override.

---

## 6. Build the Compose file

Minimum expectations:

- `name: ${APP_ID}`
- `restart: unless-stopped`
- services grouped by role
- only the routed service carries Traefik labels
- only required networks are attached

For backend/internal services:

- do not attach `proxy` by default
- do not add Traefik labels by default

---

## 7. Apply the right network model

### Public or LAN-routed stack

Verify:

- routed service joins `proxy`
- `traefik.docker.network=proxy` is set
- internal services stay on `internal` unless required otherwise

### Internal-only stack

Verify:

- no `proxy` attachment unless there is a verified reason
- no accidental route labels

---

## 8. Apply the right routing model

### Public app

Verify:

- explicit `Host()` rule
- `entrypoints=websecure`
- `tls=true`
- correct certresolver
- correct shared auth middleware, unless explicitly exempted

### LAN-only app

Verify:

- local hostname rule
- local/LAN middleware where required
- no public DNS or tunnel assumptions baked into the config

### Internal-only service

Verify:

- no public hostname
- no route labels unless the service is intentionally routed

---

## 9. Verify target port

If the service is routed through Traefik:

- confirm the in-container port the app actually listens on
- set `loadbalancer.server.port` to that exact port

Do not assume:
- port 80
- image defaults
- README examples from unrelated projects

---

## 10. Review privilege and security posture

Check whether the stack really needs:

- `ports:`
- `privileged: true`
- Docker socket mount
- host networking
- `cap_add`
- wide writable bind mounts
- root user

Prefer:

- `security_opt: [no-new-privileges:true]`
- minimum required mounts
- minimum required networks

If elevated privilege is required, document why in the stack README.

---

## 11. Add healthchecks where meaningful

For services where health matters, add a useful healthcheck.

Examples:
- HTTP check for UI
- readiness probe for API
- storage or dependency probe if no better signal exists

Do not add noisy or meaningless checks.

---

## 12. Write the stack README

Minimum README content:

- purpose of the stack
- stack class: public / LAN-only / internal-only
- main services
- required env variables
- exposed hostname, if any
- storage/volume layout
- dependencies
- any exceptions to repo policy

The README should explain the stack without forcing the reader to reverse-engineer Compose.

---

## 12a. Reuse the landing UI stylesheet for new web UIs

If the stack ships a browser-facing web UI, reuse the landing stylesheet pattern so landing and app stacks keep a consistent visual baseline.

Preferred approach:

- start from `apps/landing/site/timopoly-ui.css`
- mount or copy the stylesheet into the app web root
- include it from the app HTML before adding app-specific CSS overrides

Reference:

- `apps/landing/README_UI_REUSE.txt`

Exceptions:

- document the reason in the stack README if the app must use a different design system or vendor-owned UI

---

## 12b. Add service catalog metadata for public stacks

If the stack is a public app, create:

```text
apps/<stack>/service.meta.json
```

This file is required for public stacks so landing and other service-catalog consumers have stable human-facing metadata.

Minimum template:

```json
{
  "app.example.com": {
    "name": "Example App",
    "description": "Short human-facing summary",
    "icon": "app-icon",
    "category": "Category",
    "order": 30,
    "tags": [
      "keyword1",
      "keyword2"
    ]
  }
}
```

Verify:

- hostname key matches the intended published hostname exactly
- `name` is the human display name
- `description` is concise
- `order` is intentional
- tags are short and useful for search/filtering

---

## 13. Validate exposure

### Public app

Confirm:

- no direct HTTP port exposure
- route goes through Traefik
- intended middleware is applied
- service is not accidentally bypassing auth or TLS

### LAN-only app

Confirm:

- not publicly exposed
- local route is correct
- no accidental Cloudflare/tunnel dependency added

### Internal-only service

Confirm:

- no accidental labels
- no accidental host exposure
- not reachable externally without an intentional mechanism

---

## 14. Validate with the normal workflow

Use the repo’s standard interface:

```bash
stack up <stack>
stack ps <stack>
stack logs <stack>
```

Do not treat raw `docker compose` as the default deployment path.

---

## 15. Test the route

### Public app

Verify:
- hostname resolves as intended
- HTTPS works
- route loads through Traefik
- auth works if enabled

### LAN-only app

Verify:
- local hostname resolves
- route loads on LAN
- local middleware/access policy behaves as intended

### Internal-only service

Verify:
- dependent services can reach it if required
- it is not accidentally user-facing

---

## 16. Check for policy violations

Before finishing, review for these common mistakes:

- labels on the wrong service
- routed service missing `proxy`
- backend on `proxy` for no reason
- direct `ports:` used as a Traefik bypass
- secrets hardcoded
- shared values duplicated into local `.env`
- public service missing TLS/auth
- LAN-only service accidentally public
- internal-only service accidentally routed

---

## 17. Document exceptions

If the stack intentionally deviates from policy, document the exception in its README.

Examples:
- direct non-HTTP port exposure
- Docker socket access for a tooling service
- required elevated privileges
- unusual middleware chain
- multiple routers for a special integration path

---

## 18. Final definition of done

A new stack is complete when:

- the stack class is explicit
- Compose follows repo contracts
- routing and network choices are intentional
- env scope is correct
- security posture is reasonable
- the stack works through the intended access path
- the README documents real checked-in behavior
- no unrelated repo patterns were changed to accommodate it

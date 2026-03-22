# Known Exceptions

This file records intentional deviations from default repo policy.

Its purpose is to help humans and AI agents distinguish:
- intentional exceptions
- accidental drift
- likely policy violations

This file complements:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/policies/routing-contract.md`
- `docs/policies/env-contract.md`

---

## How to use this file

Before treating an unusual pattern as a bug or policy violation, check whether it appears here.

Examples of patterns that may be valid only by exception:

- direct `ports:` exposure
- Docker socket mounts
- `privileged: true`
- host networking
- `cap_add`
- services on `proxy` without user-facing routing
- public services without the shared auth middleware
- multiple routers/middleware chains for one stack

If a new exception is introduced, add it here and document it in the relevant stack README.

---

## Exception format

Use this format for each entry:

- stack or component
- exception type
- exact files involved
- why the exception exists
- what risk it introduces
- what guardrails still apply

---

## Current exceptions

> Add real repo-specific exceptions here as they are verified.

### Example template entry

#### Stack: example-stack
- **Exception type:** direct host port exposure
- **Files:** `apps/example-stack/compose.yml`
- **Reason:** service uses a non-HTTP protocol that Traefik does not handle in the intended deployment pattern
- **Risk:** host-level exposure outside the normal HTTP routing model
- **Guardrails:** port is limited to the required protocol only; no unrelated ports are exposed; README documents the reason

---

## Candidate exception categories

These are the most important categories to track.

### 1. Direct port exposure

Use only when:
- the service is intentionally not routed by Traefik
- the protocol is non-HTTP or otherwise intentionally host-exposed
- the reason is documented

Questions to answer:
- why can Traefik not be used?
- which exact ports are exposed?
- is the exposure LAN-only or broader?
- can the scope be narrowed?

### 2. Docker socket access

Use only when:
- the service genuinely needs Docker control or discovery

Questions to answer:
- why does the service need Docker socket access?
- is read-only sufficient?
- is there a lower-trust alternative?

### 3. Elevated privileges

Includes:
- `privileged: true`
- `cap_add`
- host devices
- root-only requirements

Questions to answer:
- what exact capability is needed?
- can the privilege be reduced?
- what is the blast radius?

### 4. Host networking

Use only when:
- there is a documented technical reason

Questions to answer:
- why can normal Docker networking not be used?
- what visibility/exposure changes result?
- what conflicts become possible?

### 5. Public exposure without shared auth

Use only when:
- the app is intentionally public without Authentik
- the reason is documented

Questions to answer:
- is the app meant to be openly accessible?
- is another auth/control mechanism being used?
- is the exposure limited to the intended hostname/path only?

### 6. Multiple routers / special middleware chains

Use only when:
- integration truly requires extra routers or path handling

Questions to answer:
- what router names exist?
- what middleware order matters?
- what breaks if simplified?

---

## Review rules

An exception should remain only if:

- it still has a real technical reason
- the reason is documented
- the risk is understood
- the exception is narrower than the obvious alternatives

If an exception no longer has a valid reason, remove it and align the stack with normal policy.

---

## Definition of done

A new exception is properly documented when:

- the exception type is clear
- exact files are named
- the reason is explicit
- the risk is described
- the remaining guardrails are stated
- the relevant stack README is updated

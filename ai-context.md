# AI Context

## Purpose

This file is supplemental orientation for AI agents working in this repository.

It is not the primary source of truth.

If this file conflicts with:

* `AGENTS.md`
* checked-in Compose files
* checked-in docs under `docs/`
* checked-in stack READMEs

prefer those files and mark any unresolved claim as **UNVERIFIED**.

---

## Authority Order

Use this order when building context:

1. `AGENTS.md`
2. relevant files under `docs/policies/`
3. relevant stack files:
   * `apps/<stack>/compose.yml`
   * `apps/<stack>/README.md`
4. `gateway/README.md`
5. relevant files under `docs/runbooks/` and `docs/architecture/`
6. this file
7. `docs/context/docker_stack_v3.9.57.txt` as historical background only

---

## Repository Model

This repository manages a single-host Docker Compose homelab.

Default layout:

* `apps/` -> application stacks
* `gateway/` -> Traefik and dynamic config
* `bin/` -> host-level tooling
* `shared/` -> shared env/secrets inputs
* `docs/` -> policies, architecture, runbooks, reference
* `state/` -> runtime state and logs

Git is the source of truth for intended configuration.

---

## Default Architecture

### Public path

Default model:

Cloudflare -> cloudflared -> Traefik -> middleware -> target service

### LAN path

Default model:

LAN client -> local DNS / AdGuard -> Traefik -> target service

### Internal path

Internal-only services should not be directly user-facing unless explicitly documented.

These are defaults, not guarantees for every stack.
Verify actual routing from checked-in Compose and gateway config.

---

## Routing Defaults

Default repo expectations:

* Traefik is the HTTP(S) entrypoint
* routed services join the external `proxy` network
* public services use explicit `Host()` rules
* public services use `websecure` and TLS
* LAN-only services should not be silently made public

Primary references:

* `docs/policies/routing-contract.md`
* `docs/policies/compose-contract.md`

Do not assume every existing stack fully complies.
Some stacks may still reflect older patterns or intentional exceptions.

---

## Authentication Defaults

Default repo expectation:

* Authentik is enforced through Traefik ForwardAuth for protected public services

Important rules:

* do not apply auth middleware to Authentik itself
* outpost endpoints must route to `authentik_proxy`
* HTTPS should be enforced before auth flow for public services

Primary references:

* `docs/policies/routing-contract.md`
* `docs/architecture/authentik.md`
* `apps/authentik/compose.yml`

Do not assume a middleware chain exists unless verified in checked-in gateway or stack config.

---

## Tooling

Primary operational interface:

```bash
stack <command> <stack>
```

Shortcut:

```bash
stk <command>
```

Useful commands:

* `stack list`
* `stack config <stack>`
* `stack up <stack>`
* `stack down <stack>`
* `stack logs <stack>`
* `stack ps <stack>`
* `stack status`
* `stack doctor <stack>`
* `stack graph <stack>`
* `stack backup <stack>`
* `stack recover <stack>`

Primary references:

* `bin/stack`
* `docs/tooling/stack-cli.md`

Important:

* use `stack` / `stk` for normal operations
* do not assume every stack requires `shared/.env.secrets`; verify against `bin/stack`

---

## Stack Classes

Before changing infra, classify the target as one of:

* public app
* LAN-only app
* internal-only service

Primary references:

* `AGENTS.md`
* `docs/policies/compose-contract.md`
* `docs/policies/routing-contract.md`

Do not infer class from name alone.
Verify from routing labels, ports, networks, and stack README.

---

## Environment Model

Default expectation:

* shared non-secret values -> `shared/.env.global`
* shared secret values -> `shared/.env.secrets`
* stack-specific values -> `apps/<stack>/.env`

Primary reference:

* `docs/policies/env-contract.md`

Do not assume an env var exists unless its presence is verified in checked-in files or docs.

---

## Exceptions and Drift

This repo contains policy docs and validation tooling, but existing stacks may not all be fully normalized.

When you encounter unusual patterns:

1. check the stack README
2. check `docs/reference/known-exceptions.md`
3. verify the actual Compose file
4. if still unclear, mark the claim as **UNVERIFIED**

Do not rewrite a stack to match policy unless the task requires it.

---

## Historical Context

`docs/context/docker_stack_v3.9.57.txt` contains historical design and operational context.

Use it for:

* migration intent
* older operational reasoning
* failure-mode background

Do not use it as the primary source of truth when it conflicts with current checked-in files.

---

## Agent Guidance

When starting a new task:

1. read `AGENTS.md`
2. read the relevant policy files
3. inspect the target stack’s checked-in `compose.yml`
4. read the target stack’s `README.md` if present
5. read gateway or runbook docs only as needed
6. use this file only as supporting orientation

When uncertain:

* say **UNVERIFIED**
* request exact files
* avoid inferring undocumented behavior

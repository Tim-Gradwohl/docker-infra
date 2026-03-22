# Environment Contract

This document defines how environment variables are used in this repository.

It complements:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/policies/routing-contract.md`

The goal is to make variable usage predictable for humans and AI agents.

---

## Purpose

Use this contract when:

- creating a new stack
- updating a Compose file
- adding a new variable
- deciding whether a value belongs in shared or stack-local env files
- validating whether secrets and non-secrets are handled correctly

---

## Environment model

This repository uses three broad categories of variables:

1. shared non-secret variables
2. shared secret variables
3. stack-local variables

The default expectation is:

- shared non-secret values live in `shared/.env.global`
- shared secret values live in `shared/.env.secrets`
- stack-specific values live in the stack’s local `.env` only when they are truly stack-specific

Do not duplicate shared values into many stack-local files without reason.

---

## Source-of-truth rules

### Rule 1 — Shared values belong in shared env files

Use `shared/.env.global` for values that are reused across stacks.

Examples include:
- timezone
- base domains
- shared middleware names
- shared certresolver names
- common UID/GID values if the repo uses them
- shared image defaults only if intentionally centralized

### Rule 2 — Secrets belong in `shared/.env.secrets`

Use `shared/.env.secrets` for sensitive values.

Examples include:
- API keys
- passwords
- tokens
- private credentials
- tunnel secrets
- database credentials
- VPN credentials

Do not place these values in:
- committed Compose files
- committed README examples containing real values
- changelog entries
- scripts unless the script intentionally reads them from env

### Rule 3 — Stack-local `.env` is only for stack-specific values

Use a stack-local `.env` only when the value is truly local to that stack.

Examples:
- `APP_ID`
- `APP_HOST`
- app-specific feature toggles
- app-specific data path names
- stack-specific model/config switches

Do not place shared repo-wide values into every stack-local `.env` by habit.

---

## Variable classes

### Shared non-secret variables

These are safe to reference broadly and are expected to be stable across stacks.

Typical examples:
- `TZ`
- `BASE_DOMAIN`
- `LAN_DOMAIN`
- `TRAEFIK_CERTRESOLVER`
- `TRAEFIK_AUTH_MIDDLEWARE`

These belong in:
- `shared/.env.global`

### Shared secret variables

These are sensitive and must not be committed with real values.

Typical examples:
- `CF_API_TOKEN`
- database passwords
- service credentials
- tunnel tokens
- VPN credentials

These belong in:
- `shared/.env.secrets`

### Stack-local variables

These describe per-stack identity or stack-only behavior.

Typical examples:
- `APP_ID`
- `APP_HOST`
- app-specific model names
- app-specific bind paths
- app-specific optional flags

These belong in:
- `apps/<stack>/.env`
- or documented examples if setup requires them

---

## Required-variable rules

If a variable is mandatory for correct behavior, prefer fail-fast interpolation.

Preferred pattern:

```yaml
environment:
  REQUIRED_VALUE: ${REQUIRED_VALUE:?REQUIRED_VALUE is required}
```

Use this when:
- the service cannot function without the value
- a missing value would cause confusing runtime failure
- the variable must be explicitly supplied

Avoid fail-fast syntax for:
- genuinely optional settings
- values with safe defaults

---

## Default-value rules

Use defaults only when the default is safe and intentional.

Preferred pattern:

```yaml
TZ: ${TZ:-Europe/Berlin}
```

Rules:

- defaults should be stable and sensible
- do not hide required infrastructure assumptions behind a casual default
- do not use a default if the real value must be explicitly chosen by the operator

Good examples:
- timezone
- optional log level
- optional certresolver name only when a repo-wide default is well-established

Bad examples:
- database password defaults
- placeholder hostnames that appear production-ready
- fake tokens or credentials

---

## Naming rules

Use clear variable names that reflect scope and purpose.

Preferred patterns:

- `APP_ID`
- `APP_HOST`
- `BASE_DOMAIN`
- `LAN_DOMAIN`
- `TRAEFIK_CERTRESOLVER`
- `TRAEFIK_AUTH_MIDDLEWARE`

Rules:

- use uppercase with underscores
- avoid ambiguous names like `HOST`, `DOMAIN`, or `TOKEN`
- prefer names that communicate whether a value is shared or stack-specific
- reuse established repo naming when possible

---

## Compose usage rules

### Rule 1 — Prefer variable-driven identity

Use variables for stack identity and routing identity where appropriate.

Examples:
- `name: ${APP_ID}`
- `Host(`${APP_HOST}.${BASE_DOMAIN}`)`

### Rule 2 — Do not hardcode secrets

Never commit real secret values into Compose.

### Rule 3 — Keep variable usage consistent

If one stack uses `APP_ID` / `APP_HOST`, do not invent an alternate naming scheme without reason.

### Rule 4 — Do not assume env values exist

A variable should be treated as available only if:
- it is defined in shared env contracts
- it is defined in stack-local `.env`
- or its existence is verified in checked-in documentation/config

If unclear, mark the use as **UNVERIFIED** and request the relevant env file or doc.

---

## Stack-local `.env` contract

A stack-local `.env` should usually contain only:

- stack identity values
- host/subdomain values
- stack-only optional settings

Example:

```dotenv
APP_ID=yt2midi_v3
APP_HOST=yt2midi-v3
TZ=Europe/Berlin
```

Rules:

- keep it minimal
- do not duplicate repo-wide values unless there is a real local override
- do not put real secrets into committed `.env.example` files
- provide `.env.example` when setup requires local customization

---

## `.env.example` rules

Use `.env.example` when a stack requires user-supplied local configuration.

Rules:

- include placeholders or safe examples only
- never include real credentials
- document which variables are required
- keep examples aligned with actual Compose usage

Good example:

```dotenv
APP_ID=myapp
APP_HOST=myapp
OPTIONAL_FEATURE=false
```

Bad example:

```dotenv
DB_PASSWORD=supersecretpassword
CF_API_TOKEN=real-token-value
```

---

## Secret-handling rules

### Never commit real secrets

This includes:
- passwords
- API keys
- VPN credentials
- private tokens
- tunnel credentials

### Never move secrets into docs for convenience

If a doc needs to describe a secret, refer to the variable name only.

Example:
- good: `Set CF_API_TOKEN in shared/.env.secrets`
- bad: pasting a real token or credential shape that looks usable

### Avoid accidental leaks in examples

Do not place secret-bearing command examples into:
- `README.md`
- `CHANGELOG.md`
- runbooks
- generated templates

---

## Documentation rules

When a stack depends on env values, document:

- which variables are required
- which are optional
- whether they are shared or stack-local
- whether they are secrets or non-secrets

A stack README should not force the reader to infer env expectations from Compose alone.

---

## Validation checklist

A variable setup is valid only when:

- shared values are in shared env files
- secrets are not hardcoded
- stack-local values are truly stack-local
- required variables use fail-fast interpolation where appropriate
- defaults are safe and intentional
- examples do not include real credentials
- variable names are consistent with repo conventions

---

## Common mistakes

### Shared value duplicated into many stacks

Problem:
- drift
- inconsistent updates
- unclear source of truth

Fix:
- move it to `shared/.env.global`

### Secret placed in stack-local committed file

Problem:
- secret exposure
- accidental Git history leak

Fix:
- move it to `shared/.env.secrets`
- rotate the secret if it was ever committed

### Required value treated as optional

Problem:
- broken runtime with confusing symptoms

Fix:
- use fail-fast interpolation
- document requirement

### Optional value treated as required for no reason

Problem:
- extra setup friction
- confusing operator experience

Fix:
- use a safe default if the setting is truly optional

### Invented variable naming

Problem:
- agent confusion
- inconsistent patterns across stacks

Fix:
- reuse established variable names where possible

---

## Preferred examples

### Compose example

```yaml
name: ${APP_ID}

services:
  app:
    image: your-image:tag
    restart: unless-stopped
    environment:
      TZ: ${TZ:-Europe/Berlin}
      REQUIRED_API_KEY: ${REQUIRED_API_KEY:?REQUIRED_API_KEY is required}
```

### Shared env example

```dotenv
TZ=Europe/Berlin
BASE_DOMAIN=example.com
LAN_DOMAIN=lan.example
TRAEFIK_CERTRESOLVER=cloudflare
TRAEFIK_AUTH_MIDDLEWARE=authentik@file
```

### Stack-local env example

```dotenv
APP_ID=myapp
APP_HOST=myapp
```

---

## Exceptions

A deviation is allowed only when:

- there is a real technical reason
- the variable scope is documented
- the change does not make secret handling less safe
- the naming remains understandable

Examples:
- a stack needs a one-off local tuning variable
- a service requires a legacy env name imposed by the upstream image

When the upstream image forces a poor variable name, document it in that stack’s README.

---

## Definition of done

An env change is complete when:

- variable scope is correct
- secrets are stored in the correct place
- Compose references are consistent
- required variables are enforced appropriately
- examples and docs match actual usage
- no unnecessary duplication was introduced

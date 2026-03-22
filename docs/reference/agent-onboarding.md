# Agent Onboarding

## Purpose

Use this file to get oriented at the start of a new agent session.

This is a navigation guide, not the primary source of truth.

If this file conflicts with checked-in repo files, prefer:

1. `AGENTS.md`
2. relevant files under `docs/policies/`
3. checked-in stack files and stack READMEs

---

## Fast Start

Read in this order:

1. `AGENTS.md`
2. `docs/policies/compose-contract.md`
3. `docs/policies/routing-contract.md`
4. `docs/policies/env-contract.md`
5. `docs/reference/known-exceptions.md`
6. target stack files:
   * `apps/<stack>/compose.yml`
   * `apps/<stack>/README.md`
   * `apps/<stack>/service.meta.json` for public stacks
7. `gateway/README.md` if routing, auth, or ingress is involved
8. relevant runbooks under `docs/runbooks/`
9. `ai-context.md` for supplemental orientation only
10. `docs/context/docker_stack_v3.9.57.txt` for historical background only

---

## What AGENTS.md Covers

`AGENTS.md` is the operating policy layer.

It tells you:

* what the source of truth is
* what not to assume
* what deployment interface to use
* how to classify stacks
* which routing, auth, env, and exposure rules matter

Read it first for constraints, not for detailed stack implementation.

---

## What The Policy Docs Cover

Use the policy docs to interpret stack intent and review changes:

* `docs/policies/compose-contract.md` -> expected Compose structure
* `docs/policies/routing-contract.md` -> routing and Traefik rules
* `docs/policies/env-contract.md` -> env and secret handling
* `docs/reference/known-exceptions.md` -> intentional deviations that are not drift

Use these before deciding whether a stack is compliant or drifting.

---

## How To Read A Stack

For a specific stack:

1. read `apps/<stack>/compose.yml`
2. read `apps/<stack>/README.md` if present
3. read `apps/<stack>/service.meta.json` if the stack is public and the file exists
4. classify it as:
   * public app
   * LAN-only app
   * internal-only service
5. verify:
   * networks
   * Traefik labels
   * ports exposure
   * middleware
   * required env vars
   * dependencies
    * service metadata coverage for public hostnames
6. check `docs/reference/known-exceptions.md` before treating unusual patterns as policy violations

Do not infer behavior from directory name alone.

---

## Routing And Auth

If the task touches ingress or auth, also read:

* `gateway/README.md`
* `docs/architecture/authentik.md`
* relevant files under `gateway/dynamic/`
* relevant runbooks under `docs/runbooks/`

Verify actual router rules and middleware from checked-in config.

---

## Tooling

Primary operational interface:

```bash
stack <command> <stack>
```

Useful references:

* `bin/stack`
* `docs/tooling/stack-cli.md`
* `bin/validate-compose-policy.sh`

For normal operations, prefer `stack` / `stk` over raw `docker compose`.

After changes, run:

```bash
bin/validate-compose-policy.sh
```

Then review the diff and update docs only where behavior or policy changed.

---

## Historical Context

These files are supplemental only:

* `ai-context.md`
* `docs/context/docker_stack_v3.9.57.txt`

Use them for:

* architectural orientation
* historical operator intent
* failure-mode background

Do not treat them as stronger than current checked-in implementation.

---

## Known Gaps

Current repo realities a new agent should expect:

* some stacks may still lack `README.md`
* policy docs may be ahead of some existing stack implementations
* unusual patterns should be checked against `docs/reference/known-exceptions.md`

When context is incomplete:

* mark the claim as **UNVERIFIED**
* request the exact missing file
* do not assume undocumented behavior

---

## Definition Of Done For Context

Before making a non-trivial change, you should know:

* the target stack class
* whether it is routed by Traefik
* whether it is public, LAN-only, or internal-only
* which env vars are required
* which services are dependencies
* whether a public stack has `service.meta.json` coverage for its published hostnames
* whether any exception is already documented in `docs/reference/known-exceptions.md`
* whether any remaining mismatch is actual drift

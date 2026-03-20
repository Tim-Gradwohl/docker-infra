# AGENTS.md — TIMOPOLY DOCKER INFRA

## PURPOSE

This file defines how AI agents must behave when working with this repository.

It is NOT a full documentation source.
It is a **behavior + rules layer**.

For architecture and implementation details, refer to:

* `ai-context.md`
* `docs/`
* `apps/*/README.md`

---

## CORE PRINCIPLES

* **Git is the single source of truth**
* **`stack` is the only deployment interface**
* **Do not rely on memory — verify everything**
* **Do not modify unrelated parts of the system**
* **Prefer minimal, targeted changes**

---

## REPO STRUCTURE

```text
apps/     → Docker Compose stacks (source of truth)
gateway/  → Traefik + dynamic configuration
bin/      → host-level tooling (stack CLI, watchdogs)
state/    → runtime state (logs, watchdog state)
shared/   → environment + secrets
docs/     → architecture, runbooks, reference
```

Rules:

* Stack-specific documentation belongs in `apps/<stack>/README.md`
* Cross-cutting documentation belongs in `docs/`
* AI context is provided via `ai-context.md`

### Context expansion

If additional context is required:

1. Use ai-context.md to identify relevant files
2. Request those files explicitly
3. Do NOT assume behavior not supported by provided files

---

## DEPLOYMENT RULES

### Primary interface

Always use:

```bash
stack <command> <stack>
```

Examples:

```bash
stack up immich
stack down metube
stack logs qbittorrentvpn
stack list
```

Shortcut:

```bash
stk <command>
```

---

### Forbidden (unless explicitly required)

* Running raw `docker compose` without env files
* Ad-hoc container manipulation outside stack tooling
* Modifying running containers directly

---

## ENVIRONMENT CONTRACT

Required env files:

* `shared/.env.global` (always)
* `shared/.env.secrets` (when required)

Rules:

* Never assume env variables exist
* If a variable is required, ensure fail-fast (`${VAR:?}`)
* Never hardcode secrets into compose files
* Never commit secrets

---

## CHANGE POLICY

When making changes:

1. **Scope strictly to the task**
2. Do NOT refactor unrelated areas
3. Preserve document integrity
4. Follow existing patterns

If a structural improvement is desired:
→ ask before applying

---

## DOCUMENTATION RULES

When updating documentation:

* Do NOT rewrite large sections unnecessarily
* Only update sections affected by the change
* Keep changelog entries accurate and scoped

### Changelog policy

* Only update the latest version section
* Do NOT modify historical entries
* Do NOT remove unrelated sections

---

## STACK RULES

* Stacks are discovered via `compose.yml`
* Located under:

  * `apps/*/compose.yml`
  * `gateway/compose.yml`

Rules:

* Do not rename stacks arbitrarily
* Do not change stack names without reason
* Keep parameterization consistent (`${APP_ID}`, etc.)

---

## NETWORKING RULES

* All HTTP traffic must go through Traefik
* Services must attach to `proxy` network for routing
* Do NOT expose container ports directly unless required

---

## AUTHENTICATION RULES

* Authentik is enforced via Traefik ForwardAuth

Rules:

* NEVER apply auth middleware to Authentik itself
* Ensure correct routing for outpost endpoints
* HTTPS must be enforced before auth flow

---

## CHANGELOG RULES

`CHANGELOG.md` is a repo-wide infrastructure history file.

### Location
- The changelog file lives at repo root:
  - `CHANGELOG.md`

### Update model
- Always add the newest release entry at the top of the file, directly below the changelog header/rules block.
- Do NOT append new releases at the bottom.
- Do NOT create separate changelog files per version, stack, or feature.

### Scope rules
Only record meaningful infrastructure-level changes, such as:
- new stacks
- new tooling or commands
- routing / proxy / auth changes
- deployment model changes
- major operational fixes
- removals of files, stacks, or workflows
- important operator-facing notes

Do NOT record:
- minor wording changes
- formatting-only edits
- trivial refactors
- raw implementation details better suited for stack docs or runbooks
- full procedures or incident narratives

### Section format
Use this structure for each version:

## <version> — <YYYY-MM-DD>

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...

### Notes
- ...

Only include sections that actually have content.

### Writing style
- Write concise, outcome-focused bullets.
- Prefer describing what changed and why it matters.
- Keep bullets short and parallel in style.
- Mention file paths or commands only when operationally useful.
- Do not paste long procedures into the changelog.

### History integrity
- Only edit the newest version block for current-session work.
- Do NOT rewrite older version entries unless correcting a clear factual error.
- Do NOT move unrelated historical content into the current version.
- Preserve historical ordering and formatting consistency.

### Session discipline
- Only include changes from the current task/session.
- If a change was discussed but not actually applied, do NOT include it.
- If uncertain whether something was truly changed, omit it or mark it UNVERIFIED outside the changelog.

### Classification guidance
- `Added` = new capability, stack, tool, file, automation
- `Changed` = behavior/config/workflow/model updates
- `Fixed` = broken behavior corrected
- `Removed` = deleted or retired items
- `Notes` = important caveat, migration note, operational insight

### Relationship to other docs
- Runbooks belong in `docs/runbooks/`
- Incidents belong in `docs/incidents/`
- Stack-specific details belong in `apps/<stack>/README.md`
- The changelog must remain a concise release history, not a full documentation file

---

## DEBUGGING GUIDELINES

### General approach

1. Verify container state
2. Verify network attachment (`proxy`)
3. Verify Traefik labels
4. Check logs
5. Validate connectivity

---

### Traefik issues

Check:

* router exists
* labels correct
* container on `proxy` network
* Traefik logs for errors

---

### VPN issues (qBittorrentVPN)

Critical rule:

```bash
ping -c1 1.1.1.1
```

If this fails:
→ VPN tunnel is broken
→ regenerate `wg0.conf`

Do NOT debug DNS first.

---

## OPERATIONAL SAFETY

* Treat containers with Docker socket access as high-trust
* Do not modify bind-mounted secrets
* Do not expose internal services externally

---

## WHEN UNCERTAIN

If any of the following occur:

* Missing file content
* Unclear configuration
* Ambiguous behavior

→ respond with:

* "UNVERIFIED"
* request:

  * raw file link
  * or local output

---

## PUBLIC MIRROR POLICY

When referencing repository content:

1. Use `raw.githubusercontent.com` links
2. Do NOT rely on memory
3. Assume branch = `main` unless specified
4. Quote exact lines when making claims (≤10 lines)

If not verified:
→ mark as **UNVERIFIED**

---

## QUICK OPERATIONS

### Deploy stack

```bash
stack up <stack>
```

### View logs

```bash
stack logs <stack>
```

### Backup

```bash
cd ~/stacks/apps/<stack>
stackbackup
```

---

## MENTAL MODEL

* Traefik = single entrypoint
* Cloudflare = external routing layer
* Authentik = authentication layer
* Docker = execution layer
* AdGuard = internal DNS

---

## DO NOT

* Do not bypass Traefik
* Do not expose containers directly
* Do not skip env files
* Do not modify unrelated stacks
* Do not assume system state without verification

---

## Repository access

The repository is available at:
https://github.com/Tim-Gradwohl/docker-infra

If additional context is required:
- request specific files
- do not assume unseen content

---

## REFERENCES

* System context → `ai-context.md`
* Architecture → `docs/architecture/`
* Runbooks → `docs/runbooks/`
* Stack-specific → `apps/<stack>/README.md`


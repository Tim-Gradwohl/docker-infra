## Stack Tools Manual
Version: 3.9.57  
Location: `~/stacks`

---

## Table of Contents

- [[#Overview]]
- [[#Tool Overview]]
- [[#Installation Layout]]
- [[#Verify Installation]]
- [[#Stack Commands]]
  - [[#Examples]]
- [[#Running Commands on All Stacks]]
- [[#Stack Status]]
- [[#Stack Diagnostics]]
- [[#Stack Graph]]
- [[#Deploying Stacks]]
- [[#Updating Stacks]]
- [[#Viewing Logs]]
- [[#Stack Backups]]
  - [[#Preferred Method]]
  - [[#Legacy Helper]]
  - [[#Backup Lifecycle]]
  - [[#Typical Maintenance Workflow]]
  - [[#Typical Recovery Workflow]]
- [[#Permission Notes]]
- [[#Helper Command]]
- [[#Useful Workflows]]
- [[#Summary]]
- [[# Stack Recover]]
  - [[#Basic Usage]]
  - [[#Typical Use Case]]
  - [[#Recovery Workflow]]
  - [[#Rollback Safety]]
  - [[#Confirmation Prompt]]
  - [[#Example Recovery]]
  - [[#Limitations]]
- [[#Stack Backup Prune]]
  - [[#Command Reference]]
  - [[#Basic Usage]]
  - [[#Prune All Stacks]]
  - [[#Retention Options]]
  - [[#Safety Options]]
  - [[#Example]]
  - [[#Typical Workflow]]
  
 [[#Setup Files]]
## Overview

This toolkit provides a unified CLI to manage Docker Compose stacks in a homelab environment.

It replaces ad-hoc `docker compose` commands with a consistent workflow and adds operational tooling such as:

- stack discovery
- controlled stack deployment
- parallel image pulling
- safe ordered startup
- stack backups
- runtime diagnostics
- service graph visualization

All stacks are stored under:

```
~/stacks
```

Typical structure:

```
~/stacks
├── apps/
│   ├── immich/
│   │   └── compose.yml
│   ├── gitea/
│   │   └── compose.yml
│   └── ...
├── gateway/
│   └── compose.yml
├── backups/
├── shared/
│   ├── .env.global
│   └── .env.secrets
└── bin/
    └── stack
```

---

## Tool Overview

Two types of tools exist.

| Tool | Type | Purpose |
|-----|-----|-----|
| `stack` | shell function + executable backend | primary CLI; supports `stack cd <stack>` when `stack-tools.sh` is sourced |
| `stk` | shell function | Shortcut to run `stack` |

Primary CLI tool:

```
stack
```

---

## Installation Layout

Main executable:

```
~/stacks/bin/stack
```

PATH configuration:

```
export PATH="$HOME/stacks/bin:$PATH"
```

Shell helper functions are sourced via:

```
source "$HOME/stacks/bin/stack-tools.sh"
```

---

## Verify Installation

Run:

```bash
which stack
type stack
type stk
```

Expected output:

```
/home/tim/stacks/bin/stack
stack is a function
stk is a function
```

---

## Stack Commands

Basic syntax:

```bash
stack <command> <stack|all> [compose_args]
```

Supported commands:

| Command | Purpose |
|------|------|
| `list` | show detected stacks |
| `status` | show runtime stack status |
| `cd` | change into a stack directory when using the sourced shell wrapper |
| `config` | validate compose configuration |
| `validate` | run compose render validation and repo policy checks |
| `doctor` | run diagnostics |
| `graph` | show stack → service tree |
| `up` | deploy stack |
| `down` | stop stack |
| `pull` | pull images |
| `restart` | restart containers |
| `logs` | show logs |
| `ps` | show containers |
| `update` | pull images, recreate containers, prune images |
| `backup` | create stack backup |

---

# Examples

```bash
stack list
stack cd immich
stack status
stack config gateway
stack validate gateway
stack validate all
stack doctor immich
stack doctor all
stack up gateway
stack up immich --remove-orphans
stack pull all
stack update immich
stack update all
stack backup immich
stack backup all
stack graph
stack logs gateway traefik
stack down metube
```

---

## Running Commands on All Stacks

Commands can target **all stacks**.

Example:

```bash
stack pull all
stack up all
stack update all
stack backup all
stack doctor all
stack graph all
stack validate all
```

Behavior:

| Command | Behavior |
|------|------|
| `pull all` | runs in parallel |
| `up all` | ordered startup |
| `update all` | pull → recreate → prune |
| `backup all` | creates backups for every stack |
| `validate all` | renders compose for all stacks, then runs repo policy checks |

Startup order priority:

```
gateway
cloudflared
authentik
others (alphabetical)
```

---

## Stack Directory Navigation

Change into a stack directory:

```bash
stack cd immich
stack cd gateway
```

Behavior:

- `stack cd <app>` changes your current shell directory only when `stack-tools.sh` has been sourced
- application stacks resolve to `~/stacks/apps/<app>`
- `stack cd gateway` resolves to `~/stacks/gateway`
- the executable backend prints the target path; the shell wrapper performs the actual `cd`

Debugging note:

- `stack` has two layers: a shell function from `stack-tools.sh` and the executable backend at `~/stacks/bin/stack`
- `which stack` shows the backend path, but `type stack` shows what your shell will actually execute
- if `stack cd` does not change directories, first check whether `stack-tools.sh` has been sourced and confirm `type stack` reports `stack is a function`

---

## Stack Status

Shows the runtime state of every stack.

```bash
stack status
```

Example:

```
STACK              STATUS
------------------ ----------------
adguardhome        [OK] running
authentik          [OK] running
cloudflared        [OK] running
gateway            [OK] running
immich             [OK] running
metube             [DOWN] stopped
```

Status meanings:

| Status | Meaning |
|------|------|
| `[OK]` | containers running |
| `[WARN]` | unhealthy container |
| `[DOWN]` | no running containers |

---

## Stack Diagnostics

Run health diagnostics.

```bash
stack doctor immich
stack doctor all
```

Example:

```
==> doctor immich
  [OK] compose config valid
  [OK] stack has running containers
  [OK] no unhealthy containers detected
  container status:
```

Doctor checks:

- compose configuration
- running containers
- container health
- service status

---

## Stack Validation

Run compose render validation plus repo policy checks.

```bash
stack validate immich
stack validate all
```

Behavior:

- `stack validate <stack>` runs `docker compose config` through the `stack` wrapper for that stack, then policy-checks the target compose file
- `stack validate all` runs compose render validation for every stack, then runs `bin/validate-compose-policy.sh` across the repo
- `bin/validate-compose-policy.sh` can still be run directly when you want only the policy checker

---

## Stack Graph

Shows stack → service layout.

```bash
stack graph
stack graph immich
stack graph all
```

Example:

```
immich
  ├── immich-server            [OK]
  ├── immich-machine-learning  [OK]
  ├── database                 [OK]
  └── redis                    [OK]
```

Another example:

```
qbittorrentvpn
  ├── pia-pf
  ├── gluetun
  ├── pf-writer
  ├── qbittorrent
  └── port-sync
```

This view is derived from:

```
docker compose config --services
```

---

## Deploying Stacks

Deploy a stack:

```bash
stack up immich
```

Equivalent to:

```
docker compose up -d
```

Deploy everything:

```bash
stack up all
```

---

## Updating Stacks

Update workflow:

```bash
stack update immich
```

Sequence:

```
pull images
recreate containers
prune unused images
```

Update everything:

```bash
stack update all
```

---

## Viewing Logs

Show logs:

```bash
stack logs immich
```

Follow logs:

```bash
stack logs immich -f
```

Equivalent Docker command:

```
docker compose logs -f
```

---

## Stack Backups

Two backup methods exist.

### Preferred method

```bash
stack backup immich
stack backup all
```

Backups stored in:

```
~/stacks/backups/apps/<stack>/
```

Example:

```
~/stacks/backups/apps/yt2midi_v3/
├── yt2midi_v3_2026-03-10_2142.tar.zst
├── yt2midi_v3_2026-03-10_2143.tar.zst
```

Compression format:

```
zstd (.tar.zst)
```

---

### Backup Lifecycle

The stack backup system follows a simple lifecycle:

```
backup → prune → recover
```

Each command serves a specific role:

| Command | Purpose |
|------|------|
| `stack backup <stack>` | Create a compressed backup archive |
| `stack backup prune <stack>` | Remove outdated backups |
| `stack recover <stack>` | Restore a stack from a backup |

---

### Typical Maintenance Workflow

A common operational workflow is:

```
stack backup all
stack backup prune all --keep 10
```

This ensures that:

- fresh backups are created
- older backups are automatically removed
- disk usage remains controlled

---

### Typical Recovery Workflow

If a stack update fails or configuration becomes corrupted:

```
stack recover <stack>
```

Example:

```
stack recover iptvnator
```

The command restores the most recent backup while preserving the previous state in:

```
~/stacks/recovered_apps/
```

---

## Permission Notes

Some containers create files owned by `root`.

In that case backups may require elevated privileges.

Example:

```bash
sudo ~/stacks/bin/stack backup all
```

Afterward fix ownership if necessary:

```bash
sudo chown -R tim:tim ~/stacks/backups
```

---

## Helper Command

`stk` is a wrapper for `stack`.

Example:

```bash
stk up immich
stk list
stk status
```

Equivalent:

```bash
stack up immich
stack list
stack status
```

---

## Useful Workflows

Update entire homelab:

```bash
stack update all
```

Pull images only:

```bash
stack pull all
```

Inspect system:

```bash
stack status
stack graph
```

Debug a stack:

```bash
stack doctor immich
stack logs immich
stack ps immich
```

Back up before maintenance:

```bash
stack backup immich
```

Back up everything:

```bash
sudo ~/stacks/bin/stack backup all
```

---

## Summary

The stack toolkit provides:

- automatic stack discovery
- centralized Docker Compose control
- consistent environment management
- parallel image pulls
- ordered startup
- automated updates
- stack backups
- runtime status overview
- stack diagnostics
- service dependency graph

Typical daily workflow:

```bash
stack status
stack doctor immich
stack update all
stack backup immich
stack graph
```

---

## Stack Recover

Restore a stack from the most recent backup archive.

This command restores the full stack directory from a backup created with `stack backup`.
It is intended for situations such as:

- broken stack configuration
- failed updates
- corrupted stack directory
- restoring a previously working state

The recovery process is designed to be **safe and reversible**.

---

### Basic Usage

Recover a stack:

```
stack recover <stack>
```

Example:

```
stack recover iptvnator
```

The tool automatically locates the **latest backup archive**.

Backups are searched in:

```
~/stacks/backups/apps/<stack>/
```

Example backup location:

```
~/stacks/backups/apps/iptvnator/
└── iptvnator_2026-03-11_1848.tar.zst
```

---

### Typical Use Case

A common workflow is restoring a stack after a failed update or configuration change.

Example scenario:

```
stack update iptvnator
```

After the update the stack fails to start or behaves incorrectly.

You can restore the last known working state with:

```
stack recover iptvnator
```

The command restores the stack directory from the latest backup while preserving the previous state in:

```
~/stacks/recovered_apps/
```

This allows quick rollback without losing the current stack data.

---

### Recovery Workflow

The recovery procedure performs several safety checks and controlled steps.

Steps performed by `stack recover`:

```
1. locate latest backup archive
2. verify archive readability
3. ask user for confirmation
4. stop the running stack
5. move current stack directory to rollback location
6. extract backup archive
7. validate compose configuration
8. start restored stack
```

This ensures the stack can be safely restored without destroying the previous state.

---

### Rollback Safety

Before restoring the backup, the current stack directory is preserved.

The existing stack directory is moved to:

```
~/stacks/recovered_apps/
```

Example rollback directory:

```
~/stacks/recovered_apps/
└── iptvnator.pre_recover_2026-03-11T18-53-49
```

This directory contains the full previous stack state and can be manually restored if needed.

Rollback directories are **not automatically deleted**.

---

### Confirmation Prompt

Because recovery replaces the current stack directory, confirmation is required.

Example prompt:

```
Recovery will replace the current stack directory for 'iptvnator'
Backup: ~/stacks/backups/apps/iptvnator/iptvnator_2026-03-11_1848.tar.zst
Current directory will be moved to:
~/stacks/recovered_apps/iptvnator.pre_recover_2026-03-11T18-53-49
Continue? [y/N]:
```

If the user answers anything other than:

```
y
```

the recovery operation is cancelled.

---

### Example Recovery

Example command:

```
stack recover iptvnator
```

Example output:

```
==> recover iptvnator
Using backup: ~/stacks/backups/apps/iptvnator/iptvnator_2026-03-11_1848.tar.zst
Archive check passed

Recovery will replace the current stack directory for 'iptvnator'
Backup: ~/stacks/backups/apps/iptvnator/iptvnator_2026-03-11_1848.tar.zst
Current directory will be moved to:
~/stacks/recovered_apps/iptvnator.pre_recover_2026-03-11T18-53-49
Continue? [y/N]: y

Stopping stack 'iptvnator'
Moving current stack to recovered_apps
Extracting backup
Validating compose config
Starting stack 'iptvnator'

Recovery completed for 'iptvnator'
Backup restored from: ~/stacks/backups/apps/iptvnator/iptvnator_2026-03-11_1848.tar.zst
Previous stack preserved at: ~/stacks/recovered_apps/iptvnator.pre_recover_2026-03-11T18-53-49
```

---

### Limitations

Recovery currently supports **one stack at a time**.

The following command is not supported:

```
stack recover all
```

Recovery is intended for **application stacks located in**:

```
~/stacks/apps/<stack>
```

Top-level stacks such as:

```
~/stacks/gateway
```

must be restored manually if required.

---

## Stack Backup Prune

Remove old stack backup archives.

The `backup prune` command helps manage disk usage by deleting outdated backup files while keeping recent backups.

Backups are stored in:

```
~/stacks/backups/apps/<stack>/
```

---

### Command Reference

| Command | Description |
|-------|-------------|
| `stack backup prune <stack>` | Remove old backups for a specific stack |
| `stack backup prune all` | Remove old backups for all stacks |
| `--keep N` | Keep the newest N backups |
| `--days N` | Delete backups older than N days |
| `--dry-run` | Show which backups would be deleted |
| `--yes` | Skip confirmation prompt |

---

## Basic Usage

Prune backups for a stack:

```
stack backup prune <stack>
```

Example:

```
stack backup prune iptvnator
```

Default behavior:

```
keep newest 10 backups
delete older backups
```

---

### Prune All Stacks

Prune backups for every stack:

```
stack backup prune all
```

---

### Retention Options

### Keep newest N backups

```
stack backup prune iptvnator --keep 5
```

Behavior:

```
keep newest 5 backups
delete older backups
```

---

### Delete backups older than N days

```
stack backup prune iptvnator --days 30
```

Behavior:

```
delete backups older than 30 days
```

---

### Safety Options

### Dry run

Preview which backups would be removed without deleting them.

```
stack backup prune iptvnator --dry-run
```

---

### Skip confirmation

Run pruning without interactive confirmation.

```
stack backup prune iptvnator --yes
```

---

### Example

Example command:

```
stack backup prune iptvnator --keep 3
```

Example output:

```
==> backup prune iptvnator
Policy: keep newest 3 backup(s)

Backups to delete:
  /home/tim/stacks/backups/apps/iptvnator/iptvnator_2026-03-10_1901.tar.zst
  /home/tim/stacks/backups/apps/iptvnator/iptvnator_2026-03-10_2103.tar.zst

Delete these 2 backup(s)? [y/N]: y

Pruned 2 backup(s) for iptvnator
```

---

### Typical Workflow

A common maintenance workflow is:

```
stack backup all
stack backup prune all --keep 10
```

This ensures that:

```
recent backups are preserved
old backups are automatically removed
disk usage stays under control
```

---

End of manual


# <mark>Setup Files</mark>

added to ~/.bashrc:

```
# add/append to ~/.bashrc:

#stack-tools
if [[ ":$PATH:" != *":$HOME/stacks/bin:"* ]]; then
    export PATH="$HOME/stacks/bin:$PATH"
fi

source "$HOME/stacks/bin/stack-tools.sh"
source "$HOME/stacks/bin/stack-completion.sh"
```

~/stacks/bin/stack:

```
# ~/stacks/bin/stack

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

PULL_JOBS="${PULL_JOBS:-4}"
RECOVERED_APPS_DIR="${ROOT}/recovered_apps"
ENV_GLOBAL="${ROOT}/shared/.env.global"
ENV_SECRETS="${ROOT}/shared/.env.secrets"

# Which stacks require secrets at deploy-time
REQUIRES_SECRETS_REGEX='^(cloudflared|authentik|gateway|immich|qbittorrentvpn|generate_piawg)$'

declare -A STACKS

discover_stacks() {
  local compose_file stack_name

  STACKS=()

  # Special top-level stack(s)
  if [[ -f "${ROOT}/gateway/compose.yml" ]]; then
    STACKS[gateway]="${ROOT}/gateway/compose.yml"
  fi

  # App stacks: ~/stacks/apps/<stack>/compose.yml
  shopt -s nullglob
  for compose_file in "${ROOT}"/apps/*/compose.yml; do
    stack_name="$(basename "$(dirname "${compose_file}")")"
    STACKS["${stack_name}"]="${compose_file}"
  done
  shopt -u nullglob
}

usage() {
  cat <<USAGE
Usage:
  stack <cmd> <stack|all> [compose_args...]

Commands:
  config     Validate/print resolved compose
  up         Deploy (up -d by default)
  down       Stop/remove stack
  pull       Pull images
  restart    Restart services
  logs       Follow logs
  ps         Show containers
  update     Pull images, recreate containers, then prune old images
  backup     Create compressed stack backup
             backup prune <stack|all> [--keep N | --days N] [--dry-run] [--yes]
  status     Show runtime status of stacks
  list       Show detected stacks
  doctor     Run health diagnostics for one stack or all stacks
  graph      Show stack → service tree
  recover    Restore stack from latest backup with rollback safety

Examples:
  stack list
  stack config gateway
  stack up gateway
  stack up immich --remove-orphans
  stack pull all
  stack update immich
  stack update all
  stack backup immich
  stack backup all
  stack logs gateway traefik
  stack down metube
  stack status
  stack doctor immich
  stack doctor all
  stack graph
  stack graph immich
  stack graph all
  stack recover immich
  stack backup prune immich
  stack backup prune immich --keep 5
  stack backup prune immich --days 30 --dry-run
  stack backup prune all --keep 10 --yes

Notes:
- Root: ${ROOT}
- Always uses: ${ENV_GLOBAL}
- Uses secrets for stacks matching: ${REQUIRES_SECRETS_REGEX} -> ${ENV_SECRETS}
- Ensure bcrypt hashes in .env.secrets escape \$ as \$\$
USAGE
}

list_stacks() {
  local s
  for s in "${!STACKS[@]}"; do
    echo "${s}"
  done | sort
}

stack_status() {
  local s
  local running_projects unhealthy_projects

  GREEN="\033[32m"
  YELLOW="\033[33m"
  RED="\033[31m"
  RESET="\033[0m"

  running_projects="$(
    docker ps --format '{{.Label "com.docker.compose.project"}}' | sort -u
  )"

  unhealthy_projects="$(
    docker ps --filter health=unhealthy \
      --format '{{.Label "com.docker.compose.project"}}' | sort -u
  )"

  printf "%-18s %s\n" "STACK" "STATUS"
  printf "%-18s %s\n" "------------------" "----------------"

  while read -r s; do
    if ! grep -Fxq "$s" <<<"$running_projects"; then
      printf "%-18s ${RED}[DOWN] stopped${RESET}\n" "$s"
    elif grep -Fxq "$s" <<<"$unhealthy_projects"; then
      printf "%-18s ${YELLOW}[WARN] unhealthy${RESET}\n" "$s"
    else
      printf "%-18s ${GREEN}[OK] running${RESET}\n" "$s"
    fi
  done < <(list_stacks)
}

stack_doctor_one() {
  local s="$1"
  local running_projects unhealthy_projects
  local GREEN YELLOW RED RESET

  GREEN="\033[32m"
  YELLOW="\033[33m"
  RED="\033[31m"
  RESET="\033[0m"

  need_files "${s}"

  running_projects="$(
    docker ps --format '{{.Label "com.docker.compose.project"}}' | sort -u
  )"

  unhealthy_projects="$(
    docker ps --filter health=unhealthy \
      --format '{{.Label "com.docker.compose.project"}}' | sort -u
  )"

  printf "\n==> doctor %s\n" "$s"

  # 1. compose file exists and env resolves
  if compose "${s}" config >/dev/null 2>&1; then
    printf "  ${GREEN}[OK]${RESET} compose config valid\n"
  else
    printf "  ${RED}[FAIL]${RESET} compose config invalid\n"
    return 1
  fi

  # 2. running / stopped
  if grep -Fxq "$s" <<<"$running_projects"; then
    printf "  ${GREEN}[OK]${RESET} stack has running containers\n"
  else
    printf "  ${RED}[DOWN]${RESET} stack has no running containers\n"
  fi

  # 3. unhealthy containers
  if grep -Fxq "$s" <<<"$unhealthy_projects"; then
    printf "  ${YELLOW}[WARN]${RESET} unhealthy container(s) detected\n"
  else
    printf "  ${GREEN}[OK]${RESET} no unhealthy containers detected\n"
  fi

  # 4. show compose ps summary
  echo "  container status:"
  compose "${s}" ps || true
}


stack_graph_one() {
  local s="$1"
  local service_count i
  local GREEN YELLOW RED RESET
  local status_output
  local -a services
  local line service state health status_text

  GREEN="\033[32m"
  YELLOW="\033[33m"
  RED="\033[31m"
  RESET="\033[0m"

  need_files "${s}"

  echo
  echo "${s}"

  mapfile -t services < <(
    compose "${s}" config --services 2>/dev/null
  )

  service_count="${#services[@]}"

  if (( service_count == 0 )); then
    echo "  [none]"
    return 0
  fi

  status_output="$(compose "${s}" ps --format '{{.Service}}|{{.State}}|{{.Health}}' 2>/dev/null || true)"

  for (( i=0; i<service_count; i++ )); do
    service="${services[$i]}"
    state=""
    health=""
    status_text=""

    while IFS='|' read -r svc st hl; do
      [[ "$svc" == "$service" ]] || continue
      state="$st"
      health="$hl"
      break
    done <<< "$status_output"

    if [[ -z "$state" ]]; then
      status_text="${RED}[DOWN]${RESET}"
    elif [[ "$health" == "unhealthy" ]]; then
      status_text="${YELLOW}[WARN]${RESET}"
    elif [[ "$state" == "running" ]]; then
      status_text="${GREEN}[OK]${RESET}"
    else
      status_text="${YELLOW}[${state^^}]${RESET}"
    fi

    if (( i == service_count - 1 )); then
      printf "  └── %-24s %b\n" "$service" "$status_text"
    else
      printf "  ├── %-24s %b\n" "$service" "$status_text"
    fi
  done
}

need_files() {
  local s="$1"

  if [[ ! -f "${ENV_GLOBAL}" ]]; then
    echo "ERROR: Missing ${ENV_GLOBAL}" >&2
    exit 1
  fi

  if [[ "${s}" =~ ${REQUIRES_SECRETS_REGEX} ]] && [[ ! -f "${ENV_SECRETS}" ]]; then
    echo "ERROR: Missing ${ENV_SECRETS} (required for stack: ${s})" >&2
    exit 1
  fi

  if [[ -z "${STACKS[$s]:-}" ]]; then
    echo "ERROR: Unknown stack '${s}'" >&2
    echo "Known stacks:" >&2
    list_stacks >&2
    echo "all" >&2
    exit 1
  fi

  if [[ ! -f "${STACKS[$s]}" ]]; then
    echo "ERROR: Missing compose file for stack '${s}': ${STACKS[$s]}" >&2
    exit 1
  fi
}

compose() {
  local stack="$1"
  shift

  local stack_dir
  stack_dir="$(dirname "${STACKS[$stack]}")"

    local args=(
    docker compose
    --project-name "${stack}"
    --env-file "${ENV_GLOBAL}"
  )

  if [[ "${stack}" =~ ${REQUIRES_SECRETS_REGEX} ]]; then
    args+=(--env-file "${ENV_SECRETS}")
  fi

  local stack_env="${stack_dir}/.env"
  if [[ -f "${stack_env}" ]]; then
    args+=(--env-file "${stack_env}")
  fi

  args+=(-f "${STACKS[$stack]}")
  args+=("$@")

  "${args[@]}"
}

backup_one() {
  local s="$1"
  local stack_dir backup_dir outfile source_dir

  need_files "${s}"

  source_dir="$(dirname "${STACKS[$s]}")"
  stack_dir="$(basename "${source_dir}")"
  backup_dir="${ROOT}/backups/apps/${stack_dir}"
  outfile="${backup_dir}/${stack_dir}_$(date +%F_%H%M).tar.zst"

  mkdir -p "${backup_dir}"

  echo "📦 Creating backup for ${stack_dir}"
  echo "   source: ${source_dir}"
  echo "   file  : ${outfile}"

  tar -I zstd -cf "${outfile}" -C "$(dirname "${source_dir}")" "${stack_dir}"

  echo "✅ Backup completed: ${outfile}"
}

backup_prune_one() {
  local s="$1"
  shift

  local source_dir stack_dir backup_dir
  local keep="10"
  local days=""
  local dry_run=0
  local assume_yes=0
  local mode="keep"
  local confirm
  local deleted_count=0
  local -a files=()
  local -a files_to_delete=()

  need_files "${s}"

  source_dir="$(dirname "${STACKS[$s]}")"
  stack_dir="$(basename "${source_dir}")"
  backup_dir="${ROOT}/backups/apps/${stack_dir}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --keep)
        [[ $# -ge 2 ]] || { echo "ERROR: --keep requires a value" >&2; return 1; }
        keep="$2"
        mode="keep"
        shift 2
        ;;
      --days)
        [[ $# -ge 2 ]] || { echo "ERROR: --days requires a value" >&2; return 1; }
        days="$2"
        mode="days"
        shift 2
        ;;
      --dry-run)
        dry_run=1
        shift
        ;;
      --yes)
        assume_yes=1
        shift
        ;;
      *)
        echo "ERROR: Unknown prune option: $1" >&2
        return 1
        ;;
    esac
  done

  if [[ -n "${days}" && "${keep}" != "10" ]]; then
    echo "ERROR: Use either --keep or --days, not both" >&2
    return 1
  fi

  if ! [[ "${keep}" =~ ^[0-9]+$ ]]; then
    echo "ERROR: --keep must be a non-negative integer" >&2
    return 1
  fi

  if [[ -n "${days}" ]] && ! [[ "${days}" =~ ^[0-9]+$ ]]; then
    echo "ERROR: --days must be a non-negative integer" >&2
    return 1
  fi

  if [[ ! -d "${backup_dir}" ]]; then
    echo "No backup directory for ${stack_dir}: ${backup_dir}"
    return 0
  fi

  mapfile -t files < <(
    find "${backup_dir}" -maxdepth 1 -type f -name "${stack_dir}_*.tar.zst" -printf '%T@ %p\n' \
      | sort -nr \
      | cut -d' ' -f2-
  )

  if (( ${#files[@]} == 0 )); then
    echo "No backups found for ${stack_dir}"
    return 0
  fi

  if [[ "${mode}" == "days" ]]; then
    mapfile -t files_to_delete < <(
      find "${backup_dir}" -maxdepth 1 -type f -name "${stack_dir}_*.tar.zst" -mtime +"${days}" | sort
    )
  else
    if (( ${#files[@]} > keep )); then
      files_to_delete=( "${files[@]:keep}" )
    else
      files_to_delete=()
    fi
  fi

  echo "==> backup prune ${s}"

  if [[ "${mode}" == "days" ]]; then
    echo "Policy: delete backups older than ${days} day(s)"
  else
    echo "Policy: keep newest ${keep} backup(s)"
  fi

  if (( ${#files_to_delete[@]} == 0 )); then
    echo "Nothing to prune for ${stack_dir}"
    return 0
  fi

  echo "Backups to delete:"
  printf '  %s\n' "${files_to_delete[@]}"

  if (( dry_run )); then
    echo "Dry run only; no files deleted"
    return 0
  fi

  if (( ! assume_yes )); then
    printf "Delete these %d backup(s)? [y/N]: " "${#files_to_delete[@]}"
    read -r confirm
    case "${confirm}" in
      y|Y|yes|YES) ;;
      *)
        echo "Prune cancelled"
        return 0
        ;;
    esac
  fi

  for f in "${files_to_delete[@]}"; do
    rm -f -- "${f}"
    ((deleted_count+=1))
  done

  echo "Pruned ${deleted_count} backup(s) for ${stack_dir}"
}

recover_one() {
  local s="$1"
  local source_dir stack_dir backup_dir backup_file
  local timestamp rollback_dir temp_extract_dir
  local confirm extracted_compose=""

  need_files "${s}"

  source_dir="$(dirname "${STACKS[$s]}")"
  stack_dir="$(basename "${source_dir}")"
  backup_dir="${ROOT}/backups/apps/${stack_dir}"

  if [[ "${source_dir}" != "${ROOT}/apps/"* ]]; then
    echo "ERROR: recover currently supports app stacks only: ${s}" >&2
    return 1
  fi

  if [[ ! -d "${backup_dir}" ]]; then
    echo "ERROR: No backup directory found for stack '${s}': ${backup_dir}" >&2
    return 2
  fi

  backup_file="$(
    find "${backup_dir}" -maxdepth 1 -type f -name "${stack_dir}_*.tar.zst" \
      | sort \
      | tail -n 1
  )"

  if [[ -z "${backup_file}" ]]; then
    echo "ERROR: No backup found for stack '${s}' in ${backup_dir}" >&2
    return 2
  fi

  timestamp="$(date +%Y-%m-%dT%H-%M-%S)"
  rollback_dir="${RECOVERED_APPS_DIR}/${stack_dir}.pre_recover_${timestamp}"

  echo "==> recover ${s}"
  echo "Using backup: ${backup_file}"

  if ! tar -I zstd -tf "${backup_file}" >/dev/null 2>&1; then
    echo "ERROR: Backup archive failed readability test: ${backup_file}" >&2
    return 3
  fi

  echo "Archive check passed"
  echo
  echo "Recovery will replace the current stack directory for '${s}'"
  echo "Backup: ${backup_file}"
  echo "Current directory will be moved to:"
  echo "  ${rollback_dir}"
  printf "Continue? [y/N]: "
  read -r confirm

  case "${confirm}" in
    y|Y|yes|YES) ;;
    *)
      echo "Recovery cancelled"
      return 4
      ;;
  esac

  mkdir -p "${RECOVERED_APPS_DIR}"

  temp_extract_dir="$(mktemp -d "${TMPDIR:-/tmp}/stack-recover-${stack_dir}-XXXXXX")"

  cleanup_recover_temp() {
    [[ -n "${temp_extract_dir:-}" && -d "${temp_extract_dir}" ]] && rm -rf "${temp_extract_dir}"
  }

  rollback_recover() {
    echo "Attempting rollback for '${s}'"

    rm -rf "${source_dir}"

    if [[ -d "${rollback_dir}" ]]; then
      mv "${rollback_dir}" "${source_dir}"
      discover_stacks
      echo "Previous stack directory restored"
      return 0
    fi

    echo "ERROR: Rollback failed: missing rollback directory: ${rollback_dir}" >&2
    return 1
  }

  trap cleanup_recover_temp RETURN

  echo "Stopping stack '${s}'"
  if ! compose "${s}" down; then
    echo "ERROR: Failed to stop stack '${s}'" >&2
    return 5
  fi

  echo "Moving current stack to recovered_apps"
  if ! mv "${source_dir}" "${rollback_dir}"; then
    echo "ERROR: Failed to move current stack to ${rollback_dir}" >&2
    return 5
  fi

  echo "Extracting backup"
  if ! tar -I zstd -xf "${backup_file}" -C "${temp_extract_dir}"; then
    echo "ERROR: Extraction failed" >&2
    rollback_recover || return 9
    discover_stacks
    return 6
  fi

  if [[ -f "${temp_extract_dir}/${stack_dir}/compose.yml" ]]; then
    mkdir -p "$(dirname "${source_dir}")"
    mv "${temp_extract_dir}/${stack_dir}" "${source_dir}"
  elif [[ -f "${temp_extract_dir}/compose.yml" ]]; then
    mkdir -p "${source_dir}"
    cp -a "${temp_extract_dir}/." "${source_dir}/"
  else
    echo "ERROR: Backup archive does not contain expected stack layout" >&2
    rollback_recover || return 9
    discover_stacks
    return 6
  fi

  discover_stacks
  need_files "${s}"

  extracted_compose="${STACKS[$s]}"

  if [[ ! -f "${extracted_compose}" ]]; then
    echo "ERROR: Restored stack does not contain a compose file" >&2
    rollback_recover || return 9
    discover_stacks
    return 7
  fi

  echo "Validating compose config"
  if ! compose "${s}" config >/dev/null; then
    echo "ERROR: Compose config validation failed for restored stack" >&2
    rollback_recover || return 9
    discover_stacks
    return 7
  fi

  echo "Starting stack '${s}'"
  if ! compose "${s}" up -d; then
    echo "ERROR: Restored stack failed to start" >&2

    if rollback_recover; then
      discover_stacks
      echo "Attempting to restart previous stack '${s}'"
      if compose "${s}" up -d; then
        echo "Recovery failed; previous stack restored and restarted"
        return 8
      else
        echo "Previous directory restored, but previous stack failed to restart" >&2
        return 9
      fi
    else
      return 9
    fi
  fi

  echo "Recovery completed for '${s}'"
  echo "Backup restored from: ${backup_file}"
  echo "Previous stack preserved at: ${rollback_dir}"
} 

run_one() {
  local cmd="$1"
  local s="$2"
  shift 2

  need_files "${s}"

  case "${cmd}" in
    config)  compose "${s}" config ;;
    up)      compose "${s}" up -d "$@" ;;
    down)    compose "${s}" down "$@" ;;
    pull)    compose "${s}" pull "$@" ;;
    restart) compose "${s}" restart "$@" ;;
    logs)    compose "${s}" logs -f "$@" ;;
    ps)      compose "${s}" ps "$@" ;;
    backup)  backup_one "${s}" ;;
    recover) recover_one "${s}" ;;
    doctor)  stack_doctor_one "${s}" ;;
    graph)   stack_graph_one "${s}" ;;
    update)
      echo "⬇ pulling images"
      compose "${s}" pull
      echo "🔄 recreating containers"
      compose "${s}" up -d "$@"
      ;;
    *)
      echo "ERROR: Unknown command '${cmd}'" >&2
      usage
      exit 1
      ;;
  esac
}

sorted_stacks_for_all() {
  local s
  local -a priority=(gateway cloudflared authentik)
  local -a others=()

  # Print priority stacks first if they exist
  for s in "${priority[@]}"; do
    [[ -n "${STACKS[$s]:-}" ]] && echo "$s"
  done

  # Collect remaining stacks
  for s in "${!STACKS[@]}"; do
    [[ " ${priority[*]} " == *" $s "* ]] && continue
    others+=("$s")
  done

  # Print remaining stacks alphabetically
  printf '%s\n' "${others[@]}" | sort
}

discover_stacks

cmd="${1:-}"
subcmd="${2:-}"

if [[ "${cmd}" == "backup" && "${subcmd}" == "prune" ]]; then
  stack="${3:-}"
  extra_args=("${@:4}")
else
  stack="${2:-}"
  extra_args=("${@:3}")
fi

if [[ "${cmd}" == "-h" || "${cmd}" == "--help" || -z "${cmd}" ]]; then
  usage
  exit 0
fi

if [[ "${cmd}" == "list" ]]; then
  list_stacks
  exit 0
fi

if [[ "${cmd}" == "status" ]]; then
  stack_status
  exit 0
fi

if [[ "${cmd}" == "graph" && -z "${stack}" ]]; then
  stack="all"
fi

if [[ -z "${stack}" ]]; then
  usage
  exit 1
fi

if [[ "${stack}" == "all" ]]; then
  if [[ "${cmd}" == "backup" && "${subcmd}" == "prune" ]]; then
    while IFS= read -r s; do
      [[ -z "${s}" ]] && continue
      backup_prune_one "${s}" "${extra_args[@]}"
    done < <(sorted_stacks_for_all)
  else
    if [[ "${cmd}" == "recover" ]]; then
      echo "ERROR: 'recover' does not support 'all'" >&2
      exit 1
    fi

    if [[ "${cmd}" == "pull" ]]; then
      pids=()

      for s in $(printf '%s\n' "${!STACKS[@]}" | sort); do
        (
          echo "==> pull ${s}"
          run_one "pull" "${s}" "${extra_args[@]}"
        ) &
        pids+=($!)

        # max parallel jobs
        if (( ${#pids[@]} >= PULL_JOBS )); then
          wait "${pids[0]}"
          pids=("${pids[@]:1}")
        fi
      done

      for pid in "${pids[@]}"; do
        wait "$pid"
      done
    else
      while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        echo "==> ${cmd} ${s}"
        run_one "${cmd}" "${s}" "${extra_args[@]}"
      done < <(sorted_stacks_for_all)
    fi
  fi
else
  if [[ "${cmd}" == "backup" && "${subcmd}" == "prune" ]]; then
    backup_prune_one "${stack}" "${extra_args[@]}"
  else
    run_one "${cmd}" "${stack}" "${extra_args[@]}"
  fi
fi

if [[ "${cmd}" == "update" ]]; then
  echo "🧹 cleaning unused images"
  docker image prune -f
fi

```

~/stacks/bin/stack-tools.sh:

```
# ~/stacks/bin/stack-tools.sh

stack() {
    local target

    if [[ "${1:-}" == "cd" ]]; then
        target="$("$HOME/stacks/bin/stack" "$@")" || return $?
        builtin cd -- "$target"
        return $?
    fi

    "$HOME/stacks/bin/stack" "$@"
}

#stack: command but shorter: stk up immich
stk() {
    stack "$@"
}
```

~/stacks/bin/stack-completion.sh:

```
# ~/stacks/bin/stack-completion.sh

_stack_completion() {
  local cur prev cmd subcmd
  local commands stacks prune_flags

  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  cmd="${COMP_WORDS[1]}"
  subcmd="${COMP_WORDS[2]}"

  commands="list status config doctor graph up down pull restart logs ps update backup recover"
  prune_flags="--keep --days --dry-run --yes"

  # Complete first argument: command
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
    return 0
  fi

  stacks="$("$HOME/stacks/bin/stack" list 2>/dev/null) all"

  # Special handling: stack backup ...
  if [[ "$cmd" == "backup" ]]; then
    if [[ $COMP_CWORD -eq 2 ]]; then
      COMPREPLY=( $(compgen -W "$stacks prune" -- "$cur") )
      return 0
    fi

    if [[ "$subcmd" == "prune" ]]; then
      if [[ $COMP_CWORD -eq 3 ]]; then
        COMPREPLY=( $(compgen -W "$stacks" -- "$cur") )
        return 0
      else
        COMPREPLY=( $(compgen -W "$prune_flags" -- "$cur") )
        return 0
      fi
    fi
  fi

  # Commands that accept stack names
  case "$cmd" in
    config|doctor|graph|up|down|pull|restart|logs|ps|update|recover)
      COMPREPLY=( $(compgen -W "$stacks" -- "$cur") )
      return 0
      ;;
    *)
      return 0
      ;;
  esac
}

complete -F _stack_completion stack
complete -F _stack_completion stk
```

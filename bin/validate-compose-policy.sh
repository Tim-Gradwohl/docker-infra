#!/usr/bin/env bash
set -euo pipefail

# validate-compose-policy.sh
#
# Lightweight repo policy checks for Compose files.
# This script is intentionally conservative and heuristic-based.
# It does not replace human review, but it helps catch obvious drift.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
KNOWN_EXCEPTIONS_FILE="$ROOT_DIR/docs/reference/known-exceptions.md"

declare -A SHARED_ENV=()

parse_env_file() {
  local file="$1"
  local map_name="$2"
  local line key value

  [[ -f "$file" ]] || return 0

  local -n map_ref="$map_name"

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    line="${line#export }"
    key="${line%%=*}"
    value="${line#*=}"

    [[ "$line" == *"="* ]] || continue

    key="$(printf '%s' "$key" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    value="$(printf '%s' "$value" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"

    if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    [[ -n "$key" ]] || continue
    map_ref["$key"]="$value"
  done < "$file"
}

resolve_var() {
  local var_name="$1"
  local stack_map_name="$2"
  local default_value="${3:-}"
  local -n stack_ref="$stack_map_name"

  if [[ -n "${stack_ref[$var_name]:-}" ]]; then
    printf '%s' "${stack_ref[$var_name]}"
    return 0
  fi

  if [[ -n "${SHARED_ENV[$var_name]:-}" ]]; then
    printf '%s' "${SHARED_ENV[$var_name]}"
    return 0
  fi

  printf '%s' "$default_value"
}

resolve_template() {
  local template="$1"
  local stack_map_name="$2"
  local token inner var_name default_value replacement

  while [[ "$template" =~ (\$\{[^}]+\}) ]]; do
    token="${BASH_REMATCH[1]}"
    inner="${token:2:${#token}-3}"
    default_value=""

    if [[ "$inner" == *":-"* ]]; then
      var_name="${inner%%:-*}"
      default_value="${inner#*:-}"
    else
      var_name="$inner"
    fi

    replacement="$(resolve_var "$var_name" "$stack_map_name" "$default_value")"
    if [[ -z "$replacement" && -z "$default_value" ]]; then
      return 1
    fi

    template="${template//$token/$replacement}"
  done

  printf '%s' "$template"
}

collect_public_hostnames() {
  local file="$1"
  local stack_dir stack_env_file line host_raw resolved
  local -n host_ref="$2"
  declare -A stack_env=()

  stack_dir="$(dirname "$file")"
  stack_env_file="$stack_dir/.env"
  parse_env_file "$stack_env_file" stack_env

  while IFS= read -r line; do
    [[ "$line" =~ Host\(\`([^\`]+)\`\) ]] || continue
    host_raw="${BASH_REMATCH[1]}"

    if ! resolved="$(resolve_template "$host_raw" stack_env)"; then
      fail "$file has an unresolved public hostname template: $host_raw"
      continue
    fi

    [[ -n "$resolved" ]] || continue
    host_ref["$resolved"]=1
  done < <(grep -E 'traefik\.http\.routers\..*rule=.*Host\(' "$file" | grep -v '^[[:space:]]*#' || true)
}

validate_service_metadata() {
  local file="$1"
  local stack_dir meta_file host meta_host
  local -A expected_hosts=()
  local -A metadata_hosts=()

  collect_public_hostnames "$file" expected_hosts

  [[ "${#expected_hosts[@]}" -gt 0 ]] || return 0

  stack_dir="$(dirname "$file")"

  if [[ "$stack_dir" == "$ROOT_DIR/gateway" ]]; then
    return 0
  fi

  meta_file="$stack_dir/service.meta.json"

  if [[ ! -f "$meta_file" ]]; then
    fail "$file is a public stack but $meta_file is missing"
    return 0
  fi

  if ! jq -e 'type == "object"' "$meta_file" >/dev/null 2>&1; then
    fail "$meta_file must contain a top-level JSON object"
    return 0
  fi

  while IFS= read -r meta_host; do
    [[ -n "$meta_host" ]] || continue
    metadata_hosts["$meta_host"]=1
  done < <(jq -r 'keys[]' "$meta_file")

  for host in "${!expected_hosts[@]}"; do
    if [[ -z "${metadata_hosts[$host]:-}" ]]; then
      fail "$meta_file is missing metadata for public hostname $host"
    fi
  done

  for meta_host in "${!metadata_hosts[@]}"; do
    if [[ -z "${expected_hosts[$meta_host]:-}" ]]; then
      fail "$meta_file contains stale metadata for hostname $meta_host"
    fi
  done
}


find_compose_files() {
  local root="${1:-$ROOT_DIR}"

  {
    if [[ -f "$root/gateway/compose.yml" ]]; then
      printf '%s\n' "$root/gateway/compose.yml"
    fi

    if [[ -d "$root/apps" ]]; then
      find "$root/apps" -type f \( -name "compose.yml" -o -name "docker-compose.yml" \) 2>/dev/null
    fi
  } | sort -u
}

warn() {
  printf 'WARN: %s\n' "$*"
}

fail() {
  printf 'FAIL: %s\n' "$*"
  FAILED=1
}

stack_name_for_file() {
  local file="$1"
  local dir

  dir="$(dirname "$file")"

  if [[ "$dir" == "$ROOT_DIR/gateway" ]]; then
    printf 'gateway'
    return 0
  fi

  basename "$dir"
}

stack_has_exception() {
  local stack="$1"
  local exception_text="$2"

  [[ -f "$KNOWN_EXCEPTIONS_FILE" ]] || return 1

  awk -v stack="$stack" -v exception="$exception_text" '
    $0 ~ "^#### Stack: " {
      in_stack = ($0 == "#### Stack: " stack)
      next
    }

    in_stack && index($0, exception) {
      found = 1
      exit
    }

    END {
      exit(found ? 0 : 1)
    }
  ' "$KNOWN_EXCEPTIONS_FILE"
}

check_file() {
  local file="$1"
  local stack_name
  local has_traefik_labels=0
  local traefik_enabled=1
  local has_proxy_network_ref=0
  local has_docker_network_label=0
  local has_ports=0
  local has_latest=0
  local has_restart=0

  stack_name="$(stack_name_for_file "$file")"

  grep -q 'traefik\.' "$file" && has_traefik_labels=1 || true
  grep -qE 'traefik\.enable[=:]"?false"?([[:space:]]|$)' "$file" && traefik_enabled=0 || true
  grep -q 'proxy' "$file" && has_proxy_network_ref=1 || true
  grep -q 'traefik\.docker\.network=proxy' "$file" && has_docker_network_label=1 || true
  grep -qE '^[[:space:]]*ports:' "$file" && has_ports=1 || true
  grep -qE 'image:.*:latest([[:space:]]|$)' "$file" && has_latest=1 || true
  grep -qE 'restart:[[:space:]]+unless-stopped' "$file" && has_restart=1 || true

  if [[ "$has_latest" -eq 1 ]]; then
    warn "$file uses a latest image tag"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$traefik_enabled" -eq 1 && "$has_docker_network_label" -eq 0 ]]; then
    fail "$file has Traefik labels but is missing traefik.docker.network=proxy"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$traefik_enabled" -eq 1 && "$has_proxy_network_ref" -eq 0 ]]; then
    fail "$file has Traefik labels but no proxy network reference"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$traefik_enabled" -eq 1 && "$has_ports" -eq 1 ]] \
    && ! stack_has_exception "$stack_name" "direct host port exposure" \
    && ! stack_has_exception "$stack_name" "published HTTP(S) ports"; then
    warn "$file has Traefik labels and direct ports; verify this is an intentional exception"
  fi

  if [[ "$has_restart" -eq 0 ]]; then
    warn "$file is missing restart: unless-stopped"
  fi

  validate_service_metadata "$file"
}

main() {
  local target
  local -a files=()

  FAILED=0

  parse_env_file "$ROOT_DIR/shared/.env.global" SHARED_ENV

  if [[ "$#" -eq 0 ]]; then
    mapfile -t files < <(find_compose_files "$ROOT_DIR")
  else
    for target in "$@"; do
      if [[ -f "$target" ]]; then
        files+=("$(cd "$(dirname "$target")" && pwd)/$(basename "$target")")
      elif [[ -d "$target" && -f "$target/compose.yml" ]]; then
        files+=("$(cd "$target" && pwd)/compose.yml")
      elif [[ -d "$target" && ( -d "$target/apps" || -f "$target/gateway/compose.yml" ) ]]; then
        while IFS= read -r file; do
          [[ -n "$file" ]] && files+=("$file")
        done < <(find_compose_files "$target")
      else
        fail "unsupported validation target: $target"
      fi
    done
  fi

  if [[ "${#files[@]}" -eq 0 ]]; then
    warn "No compose files found for validation"
    exit 0
  fi

  for file in "${files[@]}"; do
    check_file "$file"
  done

  if [[ "$FAILED" -ne 0 ]]; then
    echo
    echo "Policy validation failed."
    exit 1
  fi

  echo
  echo "Policy validation completed with no hard failures."
}

main "$@"

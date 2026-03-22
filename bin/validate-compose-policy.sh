#!/usr/bin/env bash
set -euo pipefail

# validate-compose-policy.sh
#
# Lightweight repo policy checks for Compose files.
# This script is intentionally conservative and heuristic-based.
# It does not replace human review, but it helps catch obvious drift.

#ROOT_DIR="${1:-.}"

# detect repo root (look for apps directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -d "$SCRIPT_DIR/../apps" ]]; then
  ROOT_DIR="$SCRIPT_DIR/.."
else
  ROOT_DIR="${1:-.}"
fi


find_compose_files() {
  find "$ROOT_DIR/apps" -type f \( -name "compose.yml" -o -name "docker-compose.yml" \) 2>/dev/null | sort
}

warn() {
  printf 'WARN: %s\n' "$*"
}

fail() {
  printf 'FAIL: %s\n' "$*"
  FAILED=1
}

check_file() {
  local file="$1"
  local has_traefik_labels=0
  local has_proxy_network_ref=0
  local has_docker_network_label=0
  local has_ports=0
  local has_latest=0
  local has_restart=0

  grep -q 'traefik\.' "$file" && has_traefik_labels=1 || true
  grep -q 'proxy' "$file" && has_proxy_network_ref=1 || true
  grep -q 'traefik\.docker\.network=proxy' "$file" && has_docker_network_label=1 || true
  grep -qE '^[[:space:]]*ports:' "$file" && has_ports=1 || true
  grep -qE 'image:.*:latest([[:space:]]|$)' "$file" && has_latest=1 || true
  grep -qE 'restart:[[:space:]]+unless-stopped' "$file" && has_restart=1 || true

  if [[ "$has_latest" -eq 1 ]]; then
    fail "$file uses a latest image tag"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$has_docker_network_label" -eq 0 ]]; then
    fail "$file has Traefik labels but is missing traefik.docker.network=proxy"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$has_proxy_network_ref" -eq 0 ]]; then
    fail "$file has Traefik labels but no proxy network reference"
  fi

  if [[ "$has_traefik_labels" -eq 1 && "$has_ports" -eq 1 ]]; then
    warn "$file has Traefik labels and direct ports; verify this is an intentional exception"
  fi

  if [[ "$has_restart" -eq 0 ]]; then
    warn "$file is missing restart: unless-stopped"
  fi
}

main() {
  FAILED=0

  if [[ ! -d "$ROOT_DIR/apps" ]]; then
    fail "apps directory not found under $ROOT_DIR"
    exit 1
  fi

  mapfile -t files < <(find_compose_files)

  if [[ "${#files[@]}" -eq 0 ]]; then
    warn "No compose files found under $ROOT_DIR/apps"
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

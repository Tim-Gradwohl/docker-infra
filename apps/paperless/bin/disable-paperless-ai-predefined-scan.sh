#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
STACK_CMD="${ROOT}/bin/stack"
RUNTIME_ENV="${ROOT}/apps/paperless/data/paperless-ai/.env"
CONTAINER_NAME="paperless-paperless-ai-1"
TMP_FILE="$(mktemp)"

cleanup() {
  rm -f "${TMP_FILE}"
}

trap cleanup EXIT

if [[ ! -f "${RUNTIME_ENV}" ]]; then
  echo "ERROR: Missing ${RUNTIME_ENV}" >&2
  echo "Paperless-AI has not finished bootstrap yet, or its state directory is unavailable." >&2
  exit 1
fi

awk '
BEGIN { updated = 0 }
/^PROCESS_PREDEFINED_DOCUMENTS=/ {
  print "PROCESS_PREDEFINED_DOCUMENTS=no"
  updated = 1
  next
}
{ print }
END {
  if (updated == 0) {
    print "PROCESS_PREDEFINED_DOCUMENTS=no"
  }
}
' "${RUNTIME_ENV}" > "${TMP_FILE}"

if cmp -s "${TMP_FILE}" "${RUNTIME_ENV}"; then
  echo "Paperless-AI predefined scans are already disabled in ${RUNTIME_ENV}."
else
  if mv "${TMP_FILE}" "${RUNTIME_ENV}" 2>/dev/null; then
    :
  else
    # Paperless-AI currently writes this bind-mounted file as nobody:nogroup on this host.
    # Fall back to an in-container overwrite so we can update the persisted app config.
    docker exec -i "${CONTAINER_NAME}" /bin/sh -lc "cat > /app/data/.env" < "${TMP_FILE}"
  fi
  echo "Disabled Paperless-AI predefined scans in ${RUNTIME_ENV}."
fi

"${STACK_CMD}" restart paperless paperless-ai

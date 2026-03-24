#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
STACK="${ROOT}/bin/stack"
STACK_NAME="paperless"
STACK_ENV="${ROOT}/apps/${STACK_NAME}/.env"
OLLAMA_CONTAINER="${STACK_NAME}-ollama-1"
MODEL_NAME="$(sed -n 's/^PAPERLESS_GPT_VISION_MODEL=//p' "${STACK_ENV}" | tail -n 1)"

if [[ -z "${MODEL_NAME}" ]]; then
  echo "ERROR: PAPERLESS_GPT_VISION_MODEL is not set in ${STACK_ENV}" >&2
  exit 1
fi

"${STACK}" ps "${STACK_NAME}" >/dev/null

echo "Prewarming ${MODEL_NAME} in ${OLLAMA_CONTAINER}..."
docker exec "${OLLAMA_CONTAINER}" ollama run "${MODEL_NAME}" "" >/dev/null
docker exec "${OLLAMA_CONTAINER}" ollama ps

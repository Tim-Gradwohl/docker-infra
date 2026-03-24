#!/usr/bin/env sh
set -eu

TARGET="/app/routes/setup.js"
RAG_VIEW="/app/views/rag.ejs"

if ! grep -q "'/api/rag'" "${TARGET}"; then
  python3 - <<'PY'
from pathlib import Path

path = Path("/app/routes/setup.js")
text = path.read_text()
old = """let PUBLIC_ROUTES = [
  '/health',
  '/login',
  '/logout',
  '/setup'
];"""
new = """let PUBLIC_ROUTES = [
  '/health',
  '/login',
  '/logout',
  '/setup',
  '/rag',
  '/api/rag'
];"""

if old not in text:
    raise SystemExit("Expected PUBLIC_ROUTES block not found in /app/routes/setup.js")

path.write_text(text.replace(old, new, 1))
PY
fi

if ! grep -q "OLLAMA (IDLE)" "${RAG_VIEW}"; then
  python3 - <<'PY'
from pathlib import Path

path = Path("/app/views/rag.ejs")
text = path.read_text()

old_model = """            if (statusData.ai_status === 'ok') {
                const modelName = statusData.ai_model.toUpperCase();
                aiModelName.textContent = `AI MODEL: ${modelName}`;
            } else {
                aiModelName.textContent = 'AI: Not available';
            }"""
new_model = """            if (statusData.ai_status === 'ok') {
                const modelName = statusData.ai_model
                    ? statusData.ai_model.toUpperCase()
                    : 'OLLAMA (IDLE)';
                aiModelName.textContent = `AI MODEL: ${modelName}`;
            } else {
                aiModelName.textContent = 'AI: Not available';
            }"""

old_send = """            // Check if we're connected before sending
            if (!isConnected) {
                showError("Cannot send message: Server is offline. Please check your connection.");
                return;
            }
            
            // Clear input and resize"""
new_send = """            // Let the request decide liveness; stale status checks should not block chat.
            if (!isConnected) {
                updateStatusIndicator('indexing', 'Connecting...');
            }
            
            // Clear input and resize"""

if old_model not in text:
    raise SystemExit("Expected ai_model block not found in /app/views/rag.ejs")
if old_send not in text:
    raise SystemExit("Expected sendMessage connectivity guard not found in /app/views/rag.ejs")

text = text.replace(old_model, new_model, 1)
text = text.replace(old_send, new_send, 1)
path.write_text(text)
PY
fi

cd /app
. /app/venv/bin/activate

set -- python main.py --host 127.0.0.1 --port 8000

if python3 - <<'PY'
import json
from pathlib import Path

state_path = Path("/app/data/system_state.json")
if not state_path.exists():
    raise SystemExit(1)

state = json.loads(state_path.read_text())
system_status = state.get("system_status", {})
indexing_status = state.get("indexing_status", {})

ready = (
    system_status.get("data_loaded") is True
    and system_status.get("index_ready") is True
    and system_status.get("chroma_ready") is True
    and system_status.get("bm25_ready") is True
    and indexing_status.get("documents_count", 0) > 0
)

raise SystemExit(0 if ready else 1)
PY
then
  echo "Starting Python RAG service using persisted state..."
else
  echo "Starting Python RAG service with initialization..."
  set -- "$@" --initialize
fi

"$@" &
PYTHON_PID=$!

sleep 2
echo "Python RAG service started with PID: $PYTHON_PID"

export RAG_SERVICE_URL="http://localhost:8000"
export RAG_SERVICE_ENABLED="true"

echo "Starting Node.js Paperless-AI service..."
pm2-runtime ecosystem.config.js

kill "$PYTHON_PID"

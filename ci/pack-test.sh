#!/bin/bash
set -e

# PyInstaller Packaging Test for Prompt Architect / Kayab
# Verifies that the backend can be frozen and started without dependency errors.
#
# Note: the sidecar binds a DYNAMIC port in production and announces it on
# stdout as PA_PORT=<n> (the same signal Tauri uses for discovery), so this
# test parses PA_PORT instead of assuming a fixed port.

echo "📦 Starting PyInstaller Pack Test..."

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Local runs use the project venv's PyInstaller; CI installs it globally.
if [[ -x backend/venv/bin/pyinstaller ]]; then
  export PATH="$ROOT/backend/venv/bin:$PATH"
fi

# 1. Clean previous builds
rm -rf build/ dist/

# 2. Build the backend
# Root-level onefile spec — same entry point as scripts/build_sidecar.sh
echo "🔨 Building backend with PyInstaller..."
pyinstaller pa-backend.spec --noconfirm --clean

# 3. Verify executable exists (onefile build → dist/pa-backend)
EXE_PATH="dist/pa-backend"
if [ ! -f "$EXE_PATH" ]; then
    echo "❌ FAIL: Executable not found at $EXE_PATH"
    exit 1
fi

# 4. Sanity Check: run the binary, discover its dynamic port via PA_PORT
echo "🚀 Running sanity check on binary..."
OUT_FILE="$(mktemp)"
PA_ENV=production timeout 25s "$EXE_PATH" >"$OUT_FILE" 2>&1 &
EXE_PID=$!

HEALTH_OK=0
PORT=""
for _ in $(seq 1 15); do
    if [ -z "$PORT" ]; then
        PORT=$(grep -o 'PA_PORT=[0-9]*' "$OUT_FILE" | head -1 | cut -d= -f2)
    fi
    if [ -n "$PORT" ] && curl -s "http://127.0.0.1:${PORT}/health" | grep -q '"status":"healthy"'; then
        HEALTH_OK=1
        break
    fi
    sleep 1
done

if [ "$HEALTH_OK" -eq 1 ]; then
    echo "✅ PASS: Binary started on port ${PORT} and responded to /health."
    kill $EXE_PID 2>/dev/null || true
else
    echo "❌ FAIL: Binary did not respond correctly or crashed."
    echo "---- binary output ----"
    tail -20 "$OUT_FILE"
    kill $EXE_PID 2>/dev/null || true
    exit 1
fi

rm -f "$OUT_FILE"
echo "🎉 Pack Test Completed Successfully."
exit 0

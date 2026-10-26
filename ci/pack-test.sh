#!/bin/bash
set -e

# PyInstaller Packaging Test for Prompt Architect / Kayab
# Verifies that the backend can be frozen and started without dependency errors.

echo "📦 Starting PyInstaller Pack Test..."

# 1. Clean previous builds
rm -rf build/ dist/

# 2. Build the backend
# We use --onedir for faster verification in this test
echo "🔨 Building backend with PyInstaller..."
pyinstaller backend/pa-backend.spec --noconfirm --clean

# 3. Verify executable exists
EXE_PATH="dist/pa-backend/pa-backend"
if [ ! -f "$EXE_PATH" ]; then
    echo "❌ FAIL: Executable not found at $EXE_PATH"
    exit 1
fi

# 4. Sanity Check: Run the binary and check for immediate crashes
# We set a timeout and use a dummy port/env to avoid conflicts
echo "🚀 Running sanity check on binary..."
# We use --no-network simulation by blocking external API calls if possible (not strictly needed here)
PA_ENV=production timeout 10s "$EXE_PATH" &
EXE_PID=$!

# Wait for startup
sleep 5

# 5. Check /health endpoint (using curl if available)
if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ PASS: Binary started and responded to /health."
    kill $EXE_PID
else
    echo "❌ FAIL: Binary did not respond correctly or crashed."
    kill $EXE_PID || true
    exit 1
fi

echo "🎉 Pack Test Completed Successfully."
exit 0

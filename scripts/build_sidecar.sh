#!/bin/bash
set -euo pipefail

# Build FastAPI sidecar for Tauri (one-file PyInstaller)
# Run from repository root: ./scripts/build_sidecar.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_SPEC="pa-backend.spec"
TAURI_BIN_DIR="frontend/src-tauri/binaries"
TARGET_NAME="pa-backend"

ARCH="$(uname -m)"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
# Tauri externalBin naming: e.g. pa-backend-x86_64-unknown-linux-gnu
if [[ "$OS" == "linux" ]]; then
  TAURI_TRIPLE="${ARCH}-unknown-linux-gnu"
elif [[ "$OS" == "darwin" ]]; then
  TAURI_TRIPLE="${ARCH}-apple-darwin"
else
  TAURI_TRIPLE="${ARCH}-unknown-${OS}"
fi

echo "Building sidecar for $TAURI_TRIPLE..."

if [[ ! -d backend/venv ]]; then
  echo "ERROR: backend/venv not found. Create venv and pip install -r backend/requirements.txt first."
  exit 1
fi

# shellcheck disable=SC1091
source backend/venv/bin/activate

if ! command -v pyinstaller >/dev/null 2>&1; then
  pip install pyinstaller
fi

rm -rf build/ dist/

pyinstaller --clean --noconfirm "$BACKEND_SPEC"

mkdir -p "$TAURI_BIN_DIR"

SOURCE_BIN="dist/pa-backend"
TARGET_BIN="$TAURI_BIN_DIR/${TARGET_NAME}-${TAURI_TRIPLE}"

if [[ ! -f "$SOURCE_BIN" ]]; then
  echo "ERROR: Binary not found at $SOURCE_BIN"
  ls -la dist/ || true
  exit 1
fi

cp "$SOURCE_BIN" "$TARGET_BIN"
chmod +x "$TARGET_BIN"
echo "Sidecar written to $TARGET_BIN"
ls -lh "$TARGET_BIN"
echo "Sidecar build complete."

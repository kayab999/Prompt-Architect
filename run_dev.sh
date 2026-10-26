#!/bin/bash

# Prompt Architect - Robust Development Runner
# Handles process lifecycle, signal trapping, and startup synchronization.

# Strict mode
set -euo pipefail

# Configuration
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
VENV_DIR="$BACKEND_DIR/venv"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_PID=""
FRONTEND_PID=""

# --- Colors ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[DEV-RUNNER]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# --- Cleanup Function ---
cleanup() {
    log "Shutting down services..."
    
    if [ -n "$BACKEND_PID" ]; then
        if ps -p $BACKEND_PID > /dev/null; then
            log "Killing Backend (PID: $BACKEND_PID)..."
            kill $BACKEND_PID || true
        fi
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        if ps -p $FRONTEND_PID > /dev/null; then
            log "Killing Frontend (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID || true
        fi
    fi
    
    # Extra safety: kill any process listening on the backend port
    fuser -k $BACKEND_PORT/tcp > /dev/null 2>&1 || true
    
    log "Cleanup complete."
    exit 0
}

# Trap signals
trap cleanup SIGINT SIGTERM EXIT

# --- Checks ---

# 1. Check VENV
if [ ! -d "$VENV_DIR" ]; then
    error "Virtual environment not found at $VENV_DIR."
    error "Please run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 2. Check Port Availability
if lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t >/dev/null ; then
    error "Port $BACKEND_PORT is already in use. Attempting to free it..."
    fuser -k $BACKEND_PORT/tcp || true
    sleep 1
fi

# --- Start Backend ---
log "Starting Backend..."
source "$VENV_DIR/bin/activate"
cd "$BACKEND_DIR"

# Run with entry.py to ensure PID locking and same logic as production
python entry.py --port $BACKEND_PORT &
BACKEND_PID=$!
cd ..

log "Backend started with PID: $BACKEND_PID"

# --- Wait for Health Check ---
log "Waiting for Backend to be ready..."
MAX_RETRIES=30
COUNT=0
URL="http://127.0.0.1:$BACKEND_PORT/health"

while ! curl -s $URL > /dev/null; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        error "Backend failed to start after $MAX_RETRIES seconds."
        exit 1
    fi
    echo -n "."
done
echo ""
success "Backend is UP!"

# --- Start Frontend ---
log "Starting Frontend (Tauri)..."
cd "$FRONTEND_DIR"
# Use 'npm run tauri dev' or just 'npm run dev' depending on setup. 
# Assuming 'npm run tauri dev' based on package.json having "tauri" script
npm run tauri dev &
FRONTEND_PID=$!
cd ..

log "Frontend started with PID: $FRONTEND_PID"

# --- Keep Alive ---
log "Development environment is running."
log "Press Ctrl+C to stop."

wait $FRONTEND_PID

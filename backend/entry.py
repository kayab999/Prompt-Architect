import sys
import os
import uvicorn
import argparse
import socket
import logging

# Ensure the current directory is in the path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from app.config import settings

def check_pid_lock():
    """Prevents multiple backend instances from running."""
    pid_file = settings.PID_FILE
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if the process is actually running
            os.kill(old_pid, 0)
            print(f"ERROR: Backend already running with PID {old_pid}", file=sys.stderr)
            sys.exit(1)
        except (ValueError, OSError, ProcessLookupError):
            # PID file is stale, safe to overwrite
            pid_file.unlink(missing_ok=True)

    pid_file.write_text(str(os.getpid()))

def get_free_port():
    """Finds a free port using SO_REUSEADDR to minimize race window."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prompt Architect Backend")
    parser.add_argument("--port", type=int, default=0, help="Port to run the server on (0 for dynamic)")
    args = parser.parse_args()

    check_pid_lock()

    port = args.port
    if port == 0:
        # We let uvicorn handle the binding if port is 0, but we need to know the port
        # Actually, uvicorn doesn't easily expose the assigned port before starting.
        # A better way is to bind a socket, get the port, then close it and give it to uvicorn.
        # (Race condition is minimal in local desktop app context)
        port = get_free_port()

    # The "PA_PORT" signal for Tauri discovery
    print(f"PA_PORT={port}", flush=True)

    # Run the server
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

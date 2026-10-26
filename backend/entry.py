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

def _looks_like_our_backend(pid: int) -> bool:
    """Guard against PID reuse: a live PID in the lockfile may belong to an
    unrelated process (common after a machine restart), which would otherwise
    permanently block startup. Only treat it as our backend if the command
    line matches."""
    if os.name != "posix":
        return True  # No /proc on Windows; keep the conservative behavior.
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmdline = f.read().replace(b"\x00", b" ").decode("utf-8", "replace")
    except OSError:
        return False  # vanished between the kill(0) check and now → stale
    return ("pa-backend" in cmdline) or ("entry.py" in cmdline)

def check_pid_lock():
    """Prevents multiple backend instances from running (PID-reuse safe)."""
    pid_file = settings.PID_FILE
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if the process is actually running
            os.kill(old_pid, 0)
            if _looks_like_our_backend(old_pid):
                print(f"ERROR: Backend already running with PID {old_pid}", file=sys.stderr)
                sys.exit(1)
            # Live PID but not our backend → recycled after a restart; reclaim.
            logger.warning(
                "Stale PID lock: PID %s is alive but is not Prompt Architect. Reclaiming.",
                old_pid,
            )
        except (ValueError, OSError, ProcessLookupError):
            # PID file is stale, safe to overwrite
            pass

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

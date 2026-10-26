import os
import sys
import subprocess
import signal
import time
import socket
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dev_runner")

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Global process handles
backend_process = None
frontend_process = None

def check_port_open(host, port, timeout=1.0):
    """Checks if a TCP port is open."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False

def wait_for_port(host, port, timeout=30):
    """Waits for a service to start listening on a port."""
    logger.info(f"Waiting for service at {host}:{port}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_port_open(host, port, timeout=0.1):
            logger.info(f"Service at {host}:{port} is up!")
            return True
        time.sleep(0.5)
    logger.error(f"Timed out waiting for {host}:{port}")
    return False

def get_python_executable():
    """Finds the venv python if it exists."""
    venv_python = BACKEND_DIR / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def start_backend():
    global backend_process
    logger.info("Starting Backend...")
    
    python_exe = get_python_executable()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    # We use 'exec' semantics via subprocess to ensure we can kill it
    cmd = [
        python_exe, "-m", "uvicorn", 
        "app.main:app", 
        "--reload", 
        "--reload-dir", str(BACKEND_DIR),
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    # Open log file
    log_file = open(PROJECT_ROOT / "backend.log", "w")
    
    backend_process = subprocess.Popen(
        cmd, 
        cwd=str(BACKEND_DIR), 
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    logger.info(f"Backend started with PID {backend_process.pid}")

def start_frontend():
    global frontend_process
    logger.info("Starting Frontend...")
    
    # Check for npm
    npm_cmd = "npm"
    # Windows compatibility (just in case)
    if os.name == "nt":
        npm_cmd = "npm.cmd"
        
    cmd = [npm_cmd, "run", "dev", "--", "--host"]
    
    log_file = open(PROJECT_ROOT / "frontend.log", "w")
    
    frontend_process = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        stdout=log_file, 
        stderr=subprocess.STDOUT
    )
    logger.info(f"Frontend started with PID {frontend_process.pid}")

def cleanup(signum, frame):
    logger.info("\nReceived stop signal. Cleaning up processes...")
    
    if frontend_process:
        logger.info(f"Terminating Frontend (PID {frontend_process.pid})...")
        frontend_process.terminate()
        try:
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_process.kill()
            
    if backend_process:
        logger.info(f"Terminating Backend (PID {backend_process.pid})...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            
    logger.info("All processes stopped. Exiting.")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        start_backend()
        
        # Health Check: Wait for backend before starting frontend
        # This prevents the "Connection Refused" loop in frontend
        if wait_for_port("127.0.0.1", 8000, timeout=15):
            start_frontend()
        else:
            logger.error("Backend failed to start in time. Aborting.")
            cleanup(None, None)
            
        # Keep main thread alive to handle signals and monitor children
        while True:
            if backend_process and backend_process.poll() is not None:
                logger.error("Backend process exited unexpectedly!")
                cleanup(None, None)
            if frontend_process and frontend_process.poll() is not None:
                logger.error("Frontend process exited unexpectedly!")
                cleanup(None, None)
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        cleanup(None, None)

if __name__ == "__main__":
    main()

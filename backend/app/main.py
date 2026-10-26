import os
import sys
import atexit
import logging
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.api_router import router as api_router

logger = logging.getLogger("app.main")


def cleanup_pid():
    """Removes the PID file on shutdown."""
    if settings.PID_FILE.exists():
        settings.PID_FILE.unlink(missing_ok=True)
        logger.info("Removed PID file.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("🚀 Starting Prompt Architect / Kayab Backend...")

    init_db()
    logger.info("Database initialized.")

    yield

    # Shutdown logic
    logger.info("Shutting down...")
    cleanup_pid()


# Register atexit as a safety fallback
atexit.register(cleanup_pid)

app = FastAPI(title="Prompt Architect API", version="1.0.2-rc.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:1420",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes
app.include_router(api_router)


@app.post("/shutdown")
async def shutdown(x_shutdown_key: str = Header(None)):
    """Graceful shutdown endpoint authenticated by SYSTEM_KEY."""
    if not x_shutdown_key or x_shutdown_key != settings.SYSTEM_KEY:
        raise HTTPException(status_code=403, detail="Invalid shutdown key")

    logger.info("Shutdown requested via API.")
    # Delayed signal-based exit allows response to be sent and cleanup to run
    import threading
    import time

    def delayed_exit():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=delayed_exit).start()
    return {"status": "ok", "message": "Shutting down..."}


@app.get("/status")
async def get_status():
    return {"status": "online", "version": "1.0.2-rc.1"}


@app.get("/health")
async def health():
    return {"status": "healthy"}

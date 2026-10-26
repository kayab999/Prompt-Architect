import os
import sys
import socket
import logging
import secrets
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import platformdirs
from pydantic_settings import BaseSettings
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# --- 1. Logging Setup (Immediate) ---
logger = logging.getLogger("PromptArchitect")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(console_handler)

# --- 2. Persistent Directory Setup ---
APP_NAME = "prompt_architect"
APP_AUTHOR = "Carlos"

try:
    DATA_DIR = Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))
except Exception:
    DATA_DIR = Path.home() / ".prompt_architect"

DATABASE_PATH = DATA_DIR / "prompt_library.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
LOG_FILE = DATA_DIR / "backend.log"
PID_FILE = DATA_DIR / ".pa-backend.pid"
PROFILES_DIR = DATA_DIR / "profiles"

try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.critical(f"Could not create data directories at {DATA_DIR}. Error: {e}")

# File Handler
try:
    file_handler = RotatingFileHandler(
        LOG_FILE, mode="a", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
except Exception as e:
    logger.warning(f"Could not set up file logging at {LOG_FILE}. Error: {e}")


def get_or_create_system_key() -> str:
    env_key = os.getenv("PA_SYSTEM_KEY")
    if env_key:
        return env_key

    key_file = DATA_DIR / ".system_key"
    if key_file.exists():
        return key_file.read_text().strip()

    new_key = secrets.token_urlsafe(32)
    try:
        key_file.write_text(new_key)
        if os.name != "nt":
            os.chmod(key_file, 0o600)
    except Exception as e:
        logger.warning(f"Could not save system key. {e}")
    return new_key


SYSTEM_KEY = get_or_create_system_key()


# --- 3. Ollama Connectivity Check ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))


def check_ollama_status(
    host: str = "127.0.0.1", port: int = 11434, timeout: float = 3.0
) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


OLLAMA_ONLINE = check_ollama_status()


# --- 4. Settings Class ---
class Settings:
    BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
    PROJECT_ROOT: Path = BACKEND_DIR.parent
    DATA_DIR: Path = DATA_DIR
    DB_PATH: Path = DATABASE_PATH
    LOG_FILE: Path = LOG_FILE
    PID_FILE: Path = PID_FILE
    PROFILES_DIR: Path = PROFILES_DIR
    LEGACY_LIBRARY_PATH: Path = BACKEND_DIR / "app" / "prompt_library.json"

    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    SYSTEM_KEY: str = SYSTEM_KEY
    ENV: str = os.getenv("PA_ENV", "production")
    OLLAMA_ONLINE: bool = OLLAMA_ONLINE
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "120"))
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    # Reserved flag: MicroVM tribunal is experimental and NOT wired into /generate.
    # Setting this only surfaces a clear log warning; it does not enable Firecracker.
    ENABLE_TRIBUNAL: bool = os.getenv("KAYAB_ENABLE_TRIBUNAL", "0") in (
        "1",
        "true",
        "TRUE",
        "yes",
    )
    APP_VERSION: str = "1.0.2-rc.1"

    PROFILES_PATH: Path = BACKEND_DIR / "app" / "profiles.yml"
    MODEL_PROFILES_PATH: Path = BACKEND_DIR / "model_profiles.yml"


settings = Settings()


# --- 5. KAYAB Cognitive Configuration ---
class KayabSettings(BaseSettings):
    # Primary model strategy (informational for now; /generate uses the
    # user-selected model). Must point at an installed model so the log line
    # reflects reality.
    MODEL_PRIMARY: str = "qwen2.5-coder:7b"
    MODEL_FALLBACK: str = "qwen2.5:0.5b"

    PID_OPT_IN: bool = False
    PID_KP: float = 1.0
    PID_KI: float = 0.1
    PID_KD: float = 0.05
    PID_INTEGRAL_LIMIT: float = 5.0

    MAX_LATENCY_MS: float = 5000.0
    MIN_TEMP: float = 0.1
    MAX_TEMP: float = 0.8

    model_config = {"env_prefix": "KAYAB_"}


kayab_settings = KayabSettings()

logger.info("Config loaded. Data Dir: %s", DATA_DIR)
logger.info("Ollama Online: %s", OLLAMA_ONLINE)
logger.info(
    "KAYAB Model Strategy: Primary=%s, Fallback=%s",
    kayab_settings.MODEL_PRIMARY,
    kayab_settings.MODEL_FALLBACK,
)
logger.info(
    "PID Controller: %s",
    "ENABLED" if kayab_settings.PID_OPT_IN else "DISABLED (Default)",
)
if settings.ENABLE_TRIBUNAL:
    logger.warning(
        "KAYAB_ENABLE_TRIBUNAL is set, but tribunal is experimental and NOT wired "
        "into the /generate hot path in %s. Flag is reserved for future use.",
        settings.APP_VERSION,
    )
else:
    logger.info(
        "Tribunal: not wired (RC default). App version: %s", settings.APP_VERSION
    )

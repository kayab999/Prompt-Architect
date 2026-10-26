import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration sourced from config.py
from .config import settings

import time
from .models import PromptMetadata

DB_PATH = settings.DB_PATH


def init_db():
    """Initializes the database schema and migrates legacy data if needed."""
    if not settings.DATA_DIR.exists():
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    try:
        with conn:
            # 1. Prompts Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    version INTEGER DEFAULT 1,
                    metadata TEXT,  -- JSON field for extra data like model_specifics, variables
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Execution History Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_name TEXT NOT NULL,
                    prompt_version INTEGER,
                    input_data TEXT,
                    output_data TEXT,
                    entropy_at_execution REAL,
                    pid_output REAL,
                    execution_time_ms REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. System States Table (Safety Net)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    snapshot_tag TEXT,
                    kp REAL, 
                    ki REAL, 
                    kd REAL,
                    integral_term REAL,
                    last_error REAL,
                    primary_model TEXT,
                    fallback_model TEXT,
                    is_stable BOOLEAN DEFAULT 1
                );
            """)

            # Index for faster lookups by name
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);"
            )
            logger.info(f"Database initialized at {DB_PATH}")

            # Check if migration is needed (Legacy check)
            cursor = conn.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]

            if count == 0 and settings.LEGACY_LIBRARY_PATH.exists():
                logger.info(
                    f"Found legacy library at {settings.LEGACY_LIBRARY_PATH}. Migrating..."
                )
                try:
                    with open(settings.LEGACY_LIBRARY_PATH, "r") as f:
                        data = json.load(f)

                    migrated_count = 0
                    if isinstance(data, list):
                        for entry in data:
                            name = entry.get("template", "Untitled")
                            prompt_text = entry.get("prompt", entry.get("template", ""))
                            category = entry.get("category", "General")
                            version = entry.get("version", 1)

                            meta_fields = {
                                "model_specifics": entry.get("model_specifics", {}),
                                "variables": entry.get("variables", []),
                                "guidelines": entry.get("guidelines", ""),
                                "timestamp": entry.get("timestamp", ""),
                                "signature": entry.get("signature", None),
                            }
                            metadata_json = json.dumps(meta_fields)

                            conn.execute(
                                """
                                INSERT INTO prompts (name, prompt, category, version, metadata)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (name, prompt_text, category, version, metadata_json),
                            )
                            migrated_count += 1

                    logger.info(f"Migrated {migrated_count} prompts.")
                    new_path = settings.LEGACY_LIBRARY_PATH.with_suffix(
                        ".json.migrated"
                    )
                    settings.LEGACY_LIBRARY_PATH.rename(new_path)

                except Exception as e:
                    logger.error(f"Migration failed: {e}")
    finally:
        conn.close()


def get_conn() -> sqlite3.Connection:
    """Returns a configured SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


# --- CRUD Operations ---


def list_prompts(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists prompts with pagination."""
    conn = get_conn()
    try:
        cursor = conn.execute(
            "SELECT * FROM prompts ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_prompt_by_id(prompt_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cursor = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_prompt(data: Dict[str, Any]) -> int:
    """Inserts a new prompt. 'metadata' should be a dict, will be stored as JSON string."""
    try:
        # Extract fields
        name = data.get("template", "Untitled")
        prompt_text = data.get("prompt", "")
        category = data.get("category", "General")
        version = data.get("version", 1)

        # Prepare metadata
        meta_fields = {
            "model_specifics": data.get("model_specifics", {}),
            "variables": data.get("variables", []),
            "guidelines": data.get("guidelines", ""),
            "timestamp": data.get("timestamp", ""),
            "signature": data.get("signature", {}),
        }

        validated_metadata = PromptMetadata(**meta_fields)
        metadata_json = validated_metadata.model_dump_json()

        max_retries = 5
        base_delay = 0.1

        for attempt in range(max_retries):
            conn = get_conn()
            try:
                with conn:
                    cursor = conn.execute(
                        """
                        INSERT INTO prompts (name, prompt, category, version, metadata)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (name, prompt_text, category, version, metadata_json),
                    )
                    return cursor.lastrowid
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(
                        f"Database locked. Retrying... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(base_delay * (2**attempt))
                    continue
                logger.error(f"Error inserting prompt: {e}")
                raise e
            finally:
                conn.close()

        raise sqlite3.OperationalError("Database is locked after max retries")
    except Exception as e:
        logger.error(f"Error preparing prompt: {e}")
        raise e


def parse_prompt_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to convert a DB row back to the Frontend's expected JSON format.

    DT-008 Fix: Validates metadata against PromptMetadata schema before returning.
    Corrupted metadata is sanitized to defaults instead of crashing.
    """
    try:
        raw_meta = json.loads(row["metadata"] or "{}")
        validated = PromptMetadata(**raw_meta)
        meta = validated.model_dump()
    except Exception as e:
        logger.warning(
            f"Corrupted metadata for prompt id={row.get('id')}: {e}. Sanitizing to defaults."
        )
        meta = PromptMetadata().model_dump()

    return {
        "id": row["id"],
        "template": row["name"],
        "prompt": row["prompt"],
        "category": row["category"],
        "version": row["version"],
        "model_specifics": meta.get("model_specifics", {}),
        "variables": meta.get("variables", []),
        "guidelines": meta.get("guidelines", ""),
        "timestamp": meta.get("timestamp", row["created_at"]),
        "signature": meta.get("signature", {}),
    }

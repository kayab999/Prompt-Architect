import logging
from typing import List, Optional
from datetime import datetime, timezone
from .db import get_conn
from .models import EpisodicMemory, SystemState

logger = logging.getLogger(__name__)


class HistoryDAO:
    @staticmethod
    def save_memory(memory: EpisodicMemory) -> bool:
        """
        Persists a validated EpisodicMemory into the execution_history table.
        The input MUST be a valid Pydantic model, ensuring data integrity before DB contact.
        """
        conn = get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO execution_history 
                    (prompt_name, input_data, output_data, entropy_at_execution, pid_output, execution_time_ms, timestamp) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        memory.prompt_name,
                        memory.input_data,
                        memory.output_data,
                        memory.entropy_at_execution,
                        memory.pid_output,
                        memory.execution_time_ms,
                        memory.timestamp,
                    ),
                )
            return True
        except Exception as e:
            logger.error(
                f"CRITICAL: Failed to persist Episodic Memory. Data integrity risk! Error: {e}"
            )
            return False
        finally:
            conn.close()

    @staticmethod
    def get_recent_memories(limit: int = 10) -> List[EpisodicMemory]:
        """
        Retrieves recent memories, validating them against the schema.
        Corrupted rows are logged and skipped, protecting the cognitive loop.
        """
        conn = get_conn()
        memories = []
        try:
            cursor = conn.execute(
                """
                SELECT prompt_name, input_data, output_data, entropy_at_execution, pid_output, execution_time_ms, timestamp 
                FROM execution_history 
                ORDER BY timestamp DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

            for row in rows:
                try:
                    mem = EpisodicMemory(
                        prompt_name=row["prompt_name"],
                        input_data=row["input_data"],
                        output_data=row["output_data"],
                        entropy_at_execution=row["entropy_at_execution"],
                        pid_output=row["pid_output"],
                        execution_time_ms=row["execution_time_ms"],
                        timestamp=row["timestamp"],
                    )
                    memories.append(mem)
                except Exception as val_err:
                    logger.warning(f"Found corrupted memory row: {val_err}")
                    continue

            return memories
        except Exception as e:
            logger.error(f"Failed to fetch execution history: {e}")
            return []
        finally:
            conn.close()


class StateDAO:
    @staticmethod
    def capture_state(state: SystemState) -> bool:
        """
        Persists a snapshot of the control system state.
        """
        conn = get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO system_states 
                    (snapshot_tag, kp, ki, kd, integral_term, last_error, primary_model, fallback_model, is_stable, timestamp) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        state.snapshot_tag,
                        state.kp,
                        state.ki,
                        state.kd,
                        state.integral_term,
                        state.last_error,
                        state.primary_model,
                        state.fallback_model,
                        1 if state.is_stable else 0,
                        state.timestamp or datetime.now(timezone.utc),
                    ),
                )
            return True
        except Exception as e:
            logger.error(
                f"CRITICAL: Failed to capture system state. Rollback will be impossible! Error: {e}"
            )
            return False
        finally:
            conn.close()

    @staticmethod
    def get_last_stable_state() -> Optional[SystemState]:
        """
        Retrieves the most recent stable system configuration.
        """
        conn = get_conn()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM system_states 
                WHERE is_stable = 1 
                ORDER BY timestamp DESC LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                return SystemState(
                    snapshot_tag=row["snapshot_tag"],
                    kp=row["kp"],
                    ki=row["ki"],
                    kd=row["kd"],
                    integral_term=row["integral_term"],
                    last_error=row["last_error"],
                    primary_model=row["primary_model"],
                    fallback_model=row["fallback_model"],
                    is_stable=bool(row["is_stable"]),
                    timestamp=row["timestamp"],
                )
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve stable state: {e}")
            return None
        finally:
            conn.close()

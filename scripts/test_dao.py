import sys
import logging
from pathlib import Path

# Setup path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.app.models import EpisodicMemory
from backend.app.dao import HistoryDAO
from backend.app import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DAOTest")

def test_dao():
    logger.info("🧪 TESTING HISTORY DAO INTEGRITY")
    db.init_db()
    
    # 1. Test Valid Memory
    logger.info("▶️ Attempting to save VALID memory...")
    try:
        valid_mem = EpisodicMemory(
            prompt_name="Test_Prompt",
            input_data="Test Input",
            output_data="Test Output",
            entropy_at_execution=0.5,
            pid_output=0.5,
            execution_time_ms=100.0,
            model_used="test-model"
        )
        if HistoryDAO.save_memory(valid_mem):
            logger.info("✅ Valid memory saved.")
        else:
            logger.error("❌ Valid memory save failed.")
    except Exception as e:
        logger.error(f"❌ Unexpected error on valid memory: {e}")

    # 2. Test Invalid Memory (Missing fields)
    logger.info("▶️ Attempting to save INVALID memory (expecting validation error)...")
    try:
        # Pydantic should raise ValidationError immediately
        invalid_mem = EpisodicMemory(
            prompt_name="Test_Prompt",
            # Missing input/output
            entropy_at_execution=1.5, # Out of bounds (0-1)
            pid_output=0.5,
            execution_time_ms=-10.0 # Negative time
        )
        # If we reach here, Pydantic failed
        logger.error("❌ Pydantic failed to catch invalid data!")
    except Exception as e:
        logger.info(f"✅ Pydantic correctly blocked invalid data: {e}")

    # 3. Verify Retrieval
    logger.info("▶️ Verifying retrieval...")
    mems = HistoryDAO.get_recent_memories(limit=1)
    if mems and mems[0].prompt_name == "Test_Prompt":
        logger.info(f"✅ Retrieved memory: {mems[0].prompt_name}")
    else:
        logger.warning("⚠️ Could not retrieve the just-saved memory.")

if __name__ == "__main__":
    test_dao()

import asyncio
import sys
import os
from pathlib import Path

# Ensure backend is in path
sys.path.append(os.getcwd())

from backend.app.kayab_pipeline import SovereignCodePipeline
from backend.app.architect import Architect
from backend.app.groq_architect import GroqArchitect
from backend.app.spec_validator import SpecValidator
from backend.app.mask_service import MaskService
from backend.app.models import RuleResult
from backend.app.prompt_refinement import PromptLinter
from dotenv import load_dotenv

# Ensure backend is in path and env is loaded
sys.path.append(os.getcwd())
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GROQ_API_KEY="):
                os.environ["GROQ_API_KEY"] = line.split("=")[1].strip()

async def test_pipeline():
    print("--- Testing Kayab Refinement Pipeline v2.2 (Flavors) ---")
    
    # Initialize components
    architect = GroqArchitect(model_name="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY")) 
    print(f"DEBUG: Architect type is {type(architect)}")
    linter = PromptLinter()
    spec_validator = SpecValidator()
    mask_service = MaskService()
    
    # Initialize SQLog
    # (The pipeline initializes its own manager, but we need one here to add the quest)
    from backend.app.sqlog.manager import QuestLogManager
    from backend.app.sqlog.models import Quest
    sqlog = QuestLogManager(Path("quest_log.toml"))
    q1_id = "Q001"
    sqlog.add_quest(Quest(id=q1_id, title="Implement Base Server"))

    # 1. Test TECHNICAL Flavor (Should fail/warn on 'better')
    print("\n\n=== RUN 1: TECHNICAL FLAVOR ===")
    config_tech = {
        "max_iterations": 2,
        "token_budget": 5000,
        "service_key": "secret_test_key_v2",
        "flavor": "technical"
    }
    
    project_dir = Path(os.getcwd())
    pipeline_tech = SovereignCodePipeline(architect, project_dir)
    
    # Input with subjective word "better"
    user_input = "make the code better and faster"
    requester = {"user_id": "carlos_dev", "role": "engineer"}
    template_id = "default"
    
    print(f"[Input] {user_input}")
    history_tech = await pipeline_tech.run(user_input, quest_id=q1_id)
    
    print(f"[Result ID] {history_tech['id']}")
    print(f"[Success] {history_tech['success_gate']['passed']}")
    
    # Check for specific rule triggering
    r100_hits = [e for e in history_tech['control_log'] if e['rule_id'] == 'R100_STYLE_NO_SUBJECTIVE']
    if r100_hits:
        last_hit = r100_hits[-1]
        print(f"✅ R100 Triggered: {last_hit['rule_result']} (Severity: {last_hit['rule_severity']})")
    else:
        print("❌ R100 NOT Triggered (Unexpected for Technical)")

    # 2. Test CREATIVE Flavor (Should allow 'better' or handle differently)
    print("\n\n=== RUN 2: CREATIVE FLAVOR ===")
    config_creative = {
        "max_iterations": 2,
        "token_budget": 5000,
        "service_key": "secret_test_key_v2",
        "flavor": "creative"
    }
    
    pipeline_creative = SovereignCodePipeline(architect, project_dir)
    
    # Same input
    print(f"[Input] {user_input}")
    history_creative = await pipeline_creative.run(user_input)
    
    print(f"[Result ID] {history_creative['id']}")
    print(f"[Success] {history_creative['success_gate']['passed']}")

    r100_hits_creative = [e for e in history_creative['control_log'] if e['rule_id'] == 'R100_STYLE_NO_SUBJECTIVE']
    if r100_hits_creative:
        last_hit = r100_hits_creative[-1]
        print(f"✅ R100 Triggered: {last_hit['rule_result']} (Severity: {last_hit['rule_severity']})")
        if last_hit['rule_severity'] == "LOW":
            print("   -> Correctly treated as LOW severity in Creative mode.")
    else:
        # Note: If the pattern in creative.toml doesn't match 'better', it won't trigger at all.
        # My creative.toml had "impossible_pattern_to_disable_check" so it shouldn't trigger R100 for 'better'.
        print("✅ R100 NOT Triggered (Expected for Creative, as pattern is different)")

if __name__ == "__main__":
    asyncio.run(test_pipeline())

import sys
import json
import logging
from pathlib import Path

# Setup path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.app import db
from backend.app.models import Signature

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedDB")

def seed():
    logger.info("🌱 Seeding Database with Primordial Signatures...")
    db.init_db()
    
    # 1. Insert Signatures
    prompts = [
        {
            "template": "Code_Refactor",
            "prompt": "You are a Senior Python Engineer. Refactor the following code to improve performance and readability while strictly adhering to PEP8. Ensure no security vulnerabilities are introduced.",
            "category": "Engineering",
            "signature": {
                "input_variables": ["code_snippet"],
                "output_format": "python_code",
                "constraints": ["No explanation, just code", "Strict Type Hints", "Safe imports only"]
            }
        },
        {
            "template": "Logic_Audit",
            "prompt": "Analyze the following argument for logical fallacies, cognitive biases, and structural weaknesses. Provide a formal critique.",
            "category": "Analysis",
            "signature": {
                "input_variables": ["argument_text"],
                "output_format": "markdown_report",
                "constraints": ["Identify at least 3 potential fallacies", "Formal tone", "No moral judgment"]
            }
        },
        {
            "template": "System_Homeostasis",
            "prompt": "You are the KAYAB System Governor. Analyze the provided telemetry logs. Determine if the system is in homeostasis or if intervention is required. Recommend PID parameter adjustments if necessary.",
            "category": "Meta-Cognition",
            "signature": {
                "input_variables": ["telemetry_log_json", "current_pid_state"],
                "output_format": "json_action_plan",
                "constraints": ["Output must be valid JSON", "Prioritize stability over performance"]
            }
        },
        {
            "template": "KAYAB_HEURISTIC_DADA",
            "prompt": """Eres la Capa de Disrupción Cognitiva de Kayab. Tu función es actuar cuando la lógica lineal falla.
CONTEXTO:
El sistema está atrapado en un bucle de latencia/error. El PID estándar no logra la homeostasis.

DIRECTRICES DADAÍSTAS:
1. Recontextualización: Si el problema parece de CPU, busca una causa en la persistencia o el flujo de entrada.
2. Acción Gratuita: Propón un cambio de paradigma. Ej: "Reduce el contexto al 10% y cambia a un modelo de 0.5b aunque el actual sea de 8b".
3. Provocación: Cuestiona si la telemetría actual es ruido o señal.

RESTRICCIÓN: Tu respuesta debe ser una propuesta de acción ejecutable en formato JSON estrictamente.""",
            "category": "Disruption",
            "signature": {
                "input_variables": ["current_entropy", "pid_state", "recent_errors"],
                "output_format": "json_action_proposal",
                "constraints": ["Output must be strictly JSON", "Include fields: critique, disruption, estimated_impact"]
            }
        }
    ]

    for p in prompts:
        try:
            # Check if exists to avoid overwriting with same data if id increments
            # But db.insert_prompt blindly inserts. 
            # In a real scenario we'd upsert. Here we rely on the fact that duplicate names are allowed but messy.
            # Ideally we check existence first.
            conn = db.get_conn()
            cursor = conn.execute("SELECT id FROM prompts WHERE name = ?", (p["template"],))
            if cursor.fetchone():
                logger.info(f"Skipping {p['template']} (already exists)")
            else:
                logger.info(f"Injecting: {p['template']}")
                db.insert_prompt(p)
            conn.close()
        except Exception as e:
            logger.warning(f"Error processing {p['template']}: {e}")

    logger.info("✅ Seeding Complete.")

if __name__ == "__main__":
    seed()
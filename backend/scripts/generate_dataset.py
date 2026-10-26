import os
import json
import random
import time
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

# Cargar variables (.env)
load_dotenv()

# --- CONFIGURACIÓN GRATUITA (GROQ) ---
# Nuevo Maestro (Más inteligente aún)
TEACHER_MODEL = "llama-3.3-70b-versatile" 

# Nuevo Aprendiz (Más rápido)
STUDENT_MODEL = "llama-3.1-8b-instant"

# Archivos de salida
GOLD_DATA_FILE = "gold_standard_examples.jsonl"
FINAL_DATASET_FILE = "training_dataset.jsonl"

# Cantidad (Ajusta según tu paciencia, Groq es rápido pero tiene rate limits por minuto)
NUM_GOLD_EXAMPLES = 50       
NUM_BULK_EXAMPLES = 500      

# Cliente Groq
# Obtén tu key gratis en: https://console.groq.com/keys
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# --- PROMPTS ---

SYSTEM_PROMPT_TEACHER = """
You are an expert Prompt Engineer. Your goal is to take a simple, vague user request and transform it into a highly detailed, structured, and effective prompt for an LLM.

Output ONLY a JSON object with two keys:
- "input": A realistic simple user prompt (e.g. "write a poem about cats").
- "output": The optimized, expert-level prompt structure (e.g. "Act as a poet...").
Do not output markdown code blocks, just the raw JSON.
"""

def generate_gold_standard(n: int):
    """Genera ejemplos de alta calidad usando el modelo Maestro (Llama 70B)."""
    print(f"💎 Generando {n} ejemplos 'Gold Standard' GRATIS con {TEACHER_MODEL}...")
    examples = []
    
    topics = ["python coding", "creative writing", "data analysis", "marketing copy", "academic writing"]
    
    for i in range(n):
        topic = random.choice(topics)
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_TEACHER},
                    {"role": "user", "content": f"Generate one high-quality example pair (simple vs expert) related to: {topic}. Return JSON only."}
                ],
                model=TEACHER_MODEL,
                temperature=0.7,
                response_format={"type": "json_object"} # Groq soporta modo JSON nativo
            )
            
            content = chat_completion.choices[0].message.content
            data = json.loads(content)
            examples.append(data)
            print(f"   ✓ Ejemplo {i+1}/{n} listo.")
            
            # Pequeña pausa para respetar los rate-limits de la capa gratuita
            time.sleep(2) 

        except Exception as e:
            print(f"   ✗ Error en ejemplo {i+1}: {e}")
            time.sleep(5) # Pausa más larga si hay error

    # Guardar
    with open(GOLD_DATA_FILE, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + '\n')
    
    return examples

def generate_bulk_dataset(gold_examples: List[Dict], n: int):
    """Usa los ejemplos Gold para generar volumen con el modelo rápido (Llama 8B)."""
    print(f"🚀 Iniciando generación masiva ({n} items) con {STUDENT_MODEL}...")
    
    with open(FINAL_DATASET_FILE, 'a') as f:
        for i in range(n):
            shots = random.sample(gold_examples, min(3, len(gold_examples)))
            
            few_shot_prompt = "Examples of Simple to Expert prompt conversion:\n"
            for shot in shots:
                few_shot_prompt += f"Input: {shot['input']}\nOutput: {shot['output']}\n---\n"
            
            user_task = "Generate a NEW, UNIQUE pair (Input/Output) following this style. Return ONLY JSON."

            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant. Output JSON only."},
                        {"role": "user", "content": few_shot_prompt + user_task}
                    ],
                    model=STUDENT_MODEL,
                    temperature=0.8,
                    response_format={"type": "json_object"}
                )
                
                content = chat_completion.choices[0].message.content
                data = json.loads(content)
                f.write(json.dumps(data) + '\n')
                
                if (i+1) % 10 == 0:
                    print(f"   ✓ {i+1}/{n} datos generados.")
                
                # Pausa anti-rate-limit (la capa gratuita suele limitar a 30 req/min)
                time.sleep(1.5) 

            except Exception as e:
                print(f"   ✗ Error (probablemente rate limit, reintentando...): {e}")
                time.sleep(10)

def main():
    # Since we're creating the script in a directory that may not exist, let's cd into it
    # to ensure the output files are created in the right place.
    # A better approach would be to construct absolute paths for files.
    
    # Let's get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    gold_file_path = os.path.join(script_dir, GOLD_DATA_FILE)
    final_dataset_path = os.path.join(script_dir, FINAL_DATASET_FILE)


    if os.path.exists(gold_file_path):
        print("📂 Cargando ejemplos Gold existentes...")
        gold_examples = []
        with open(gold_file_path, 'r') as f:
            for line in f:
                gold_examples.append(json.loads(line))
    else:
        gold_examples = generate_gold_standard(NUM_GOLD_EXAMPLES)

    generate_bulk_dataset(gold_examples, NUM_BULK_EXAMPLES)
    print(f"\n✅ ¡Milagro completado! Dataset guardado en: {FINAL_DATASET_FILE}")

if __name__ == "__main__":
    main()

import re
import json
import sys
import os
from typing import List, Dict, Any

# --- CONFIGURACIÓN ---
# Detectamos rutas relativas al script para evitar errores de "File not found"
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # backend/scripts
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR)) # root
INPUT_FILE = os.path.join(PROJECT_ROOT, "deep_research_report.md")
# Destino: backend/app/prompt_library.json (para que esté junto al código de la app)
OUTPUT_FILE = os.path.join(os.path.dirname(BASE_DIR), "app", "prompt_library.json")

# --- PATRONES REGEX (FLEXIBILIDAD) ---
# Captura "## Nombre Categoria" ignorando numeros iniciales
RX_CATEGORY = re.compile(r'^##\s+(?:\d+\.?\d*\s*)?(.*)', re.IGNORECASE)
# Captura variaciones de "### 1.1 Template Structure"
RX_TEMPLATE_START = re.compile(r'^###\s+.*Template Structure', re.IGNORECASE)
# Captura variaciones de "### 1.2 Implementation Guidelines"
RX_GUIDELINES_START = re.compile(r'^###\s+.*Implementation Guidelines', re.IGNORECASE)
# Detecta cualquier otro subtítulo (fin de sección)
RX_SECTION_END = re.compile(r'^###\s+', re.IGNORECASE)

def parse_markdown_report(text: str) -> List[Dict[str, Any]]:
    entries = []
    current_entry = {}
    
    current_category = "General"
    buffer = []
    mode = "SEARCHING" # SEARCHING, READING_TEMPLATE, READING_GUIDELINES
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # 1. Detección de Categoría
        cat_match = RX_CATEGORY.match(line)
        if cat_match and "Template Structure" not in line:
            if current_entry and "template" in current_entry:
                save_current_buffer(current_entry, mode, buffer)
                entries.append(current_entry)
            
            current_category = cat_match.group(1).strip()
            current_entry = {"category": current_category, "model_specifics": {}}
            mode = "SEARCHING"
            buffer = []
            continue

        # 2. Inicio de Template
        if RX_TEMPLATE_START.match(line):
            save_current_buffer(current_entry, mode, buffer) # Guardar lo anterior si existía
            mode = "READING_TEMPLATE"
            buffer = []
            continue

        # 3. Inicio de Guidelines
        if RX_GUIDELINES_START.match(line):
            if mode == "READING_TEMPLATE":
                full_template = "\n".join(buffer).strip().strip('"\'')
                current_entry["template"] = full_template
                # Extraer variables {Variable}
                current_entry["variables"] = list(set(re.findall(r'\{([a-zA-Z0-9_]+)\}', full_template)))
            
            mode = "READING_GUIDELINES"
            buffer = []
            continue

        # 4. Fin de sección (cualquier otro H3 que no sea los anteriores)
        if RX_SECTION_END.match(line) and not RX_TEMPLATE_START.match(line) and not RX_GUIDELINES_START.match(line):
             save_current_buffer(current_entry, mode, buffer)
             mode = "SEARCHING"
             buffer = []
        
        # 5. Captura de contenido
        if mode in ["READING_TEMPLATE", "READING_GUIDELINES"]:
            if line and not line.startswith("#"):
                buffer.append(line)

    # Guardar última entrada
    save_current_buffer(current_entry, mode, buffer)
    if current_entry and "template" in current_entry:
        entries.append(current_entry)

    return entries

def save_current_buffer(entry, mode, buffer):
    if not buffer: return
    content = "\n".join(buffer).strip()
    if mode == "READING_TEMPLATE" and "template" not in entry:
        entry["template"] = content.strip('"\'')
        entry["variables"] = list(set(re.findall(r'\{([a-zA-Z0-9_]+)\}', content)))
    elif mode == "READING_GUIDELINES":
        entry["guidelines"] = content

def validate_data(data: List[Dict[str, Any]]) -> bool:
    if not data:
        print("🔴 Error: No se extrajeron entradas.")
        return False
    
    print(f"🔍 Validando {len(data)} entradas...")
    valid_count = 0
    for idx, item in enumerate(data):
        if not item.get("template"):
            print(f"🔸 Advertencia: Entrada #{idx} ({item.get('category', 'Unknown')}) no tiene template.")
        else:
            # Asegurar timestamp y versión para compatibilidad con la app
            if "version" not in item: item["version"] = 1
            if "timestamp" not in item: item["timestamp"] = "2026-01-02T00:00:00"
            if "prompt" not in item: item["prompt"] = item["template"] # Mapping template -> prompt
            valid_count += 1
            
    print(f"🟢 Datos válidos: {valid_count}/{len(data)}")
    return valid_count > 0

def main():
    print(f"📂 Leyendo: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except FileNotFoundError:
        print(f"🔴 Error: No se encuentra '{INPUT_FILE}'. Crea el reporte primero.")
        sys.exit(1)

    structured_data = parse_markdown_report(raw_text)
    
    if validate_data(structured_data):
        # Asegurar que el directorio de destino existe
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Base de datos generada en: {OUTPUT_FILE}")
    else:
        print("⚠️ Proceso abortado por falta de datos válidos.")

if __name__ == "__main__":
    main()

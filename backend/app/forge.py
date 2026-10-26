import tomllib
import json
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from .architect import Architect

logger = logging.getLogger(__name__)

class ConstitutionForge:
    """
    Componente encargado de forjar la 'Constitución' del proyecto.
    Refactored: Added path sanitation.
    """
    
    def __init__(self, architect):
        self.architect = architect
        self.meta_const_path = Path(__file__).parent / "rules/meta_constitution.toml"
        self.base_projects_dir = Path("~/.local/share/prompt_architect/projects").expanduser()

    def _sanitize_project_name(self, name: str) -> str:
        # Allow only alphanumeric, underscore, and dash
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        if not sanitized:
            raise ValueError("Invalid project name")
        return sanitized

    async def forge_constitution(self, user_intent: str, project_name: str, flavor: str = "default") -> str:
        # Sanitize name
        sanitized_name = self._sanitize_project_name(project_name)
        
        # Build and validate path
        project_dir = (self.base_projects_dir / sanitized_name).resolve()
        
        # Ensure path is within allowed base
        if not str(project_dir).startswith(str(self.base_projects_dir.resolve())):
            raise ValueError("Path traversal detected")
        
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Meta-Prompt construction with vocabulary-controlled constraints
        meta_prompt = f"""
        Eres un Arquitecto de Sistemas Soberanos. Redacta la Constitución (`project.toml`) para: {user_intent}
        
        Debes usar EXACTAMENTE este vocabulario de invariantes permitidas:
        no_unsafe_blocks, frame_length_prefixing, arena_reset_interval, pydantic_first, forbidden_patterns, required_derives.
        
        Formato requerido:
        [project]
        name = "{project_name}"
        description = "..."
        language = "rust"
        
        [contracts]
        # ...
        
        [invariants]
        # Solo usa las claves permitidas arriba
        
        [tests_destructivos]
        commands = [...]
        
        [metrics]
        blast_radius_target = 0
        recovery_time_ms = 5000
        """

        # 2. Invoke Architect
        draft = await self.architect.generate(meta_prompt)
        toml_content = draft.get("raw_text", "")

        # 3. Validation logic (Structural + Semantic)
        try:
            parsed_toml = tomllib.loads(toml_content)
        except Exception as e:
            logger.error(f"Failed to parse TOML: {e}")
            raise ValueError("Invalid TOML structure generated")

        # Basic Semantic validation against meta_constitution
        with open(self.meta_const_path, "rb") as f:
            meta_const = tomllib.load(f)
            
        self._validate_against_meta(parsed_toml, meta_const)

        # 4. Save and Sign
        toml_path = project_dir / "project.toml"
        with open(toml_path, "w") as f:
            f.write(toml_content)
            
        self._create_manifest(project_dir, toml_content, user_intent, meta_prompt)

        return str(toml_path)

    def _validate_against_meta(self, generated_toml: dict, meta_const: dict):
        # Validate Invariants against allowed list
        generated_invariants = generated_toml.get("invariants", {})
        allowed = meta_const["invariant_validation"]["allowed_invariants"]
        
        for inv in generated_invariants.keys():
            if inv not in allowed:
                raise ValueError(f"Invariant '{inv}' not allowed in meta-constitution.")

    def _create_manifest(self, project_dir: Path, toml_content: str, intent: str, prompt: str):
        manifest = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": intent,
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
            "toml_hash": hashlib.sha256(toml_content.encode()).hexdigest(),
        }
        
        # Sign with integrity_key (mocking system_key retrieval)
        from .config import settings as _settings

        signing_key = os.getenv("PA_SYSTEM_KEY") or os.getenv("SYSTEM_KEY") or _settings.SYSTEM_KEY
        
        manifest_json = json.dumps(manifest, sort_keys=True)
        signature = hmac.new(
            signing_key.encode(), manifest_json.encode(), hashlib.sha256
        ).hexdigest()
        
        manifest["signature"] = signature
        
        with open(project_dir / "manifest.toml", "w") as f:
            json.dump(manifest, f, indent=4)

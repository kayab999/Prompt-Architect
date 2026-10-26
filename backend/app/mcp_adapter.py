"""
MCP Adapter — Bridge between Kayab pipeline and REST endpoints.

This module provides a unified interface that:
1. Instantiates the correct Architect (Ollama or Groq) based on model selection
2. Runs the PromptRefinementPipeline and returns simplified results
3. Exposes DB operations (list_prompts) for library endpoints
4. Provides model listing (Ollama local + Groq known models)

All endpoints in api_router.py should use this adapter, never call Kayab directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .config import settings
from .db import list_prompts, parse_prompt_row
from .groq_architect import GroqArchitect
from .kayab_pipeline import PromptRefinementPipeline, SovereignCodePipeline
from .model_profiles import ModelProfileService
from .ollama_architect import OllamaArchitect, _extract_models
from .prompt_refinement import PromptLinter
from .services import MaskService, RuleLoader, SpecValidator

logger = logging.getLogger(__name__)

# Re-export for tests that may import pipeline name
__all__ = [
    "run_refinement",
    "get_available_models",
    "get_profiles",
    "get_library",
    "get_presets",
    "compile_visual",
    "GROQ_MODELS",
    "SovereignCodePipeline",
    "PromptRefinementPipeline",
]

GROQ_MODELS = [
    # Production text models on Groq (verified against console.groq.com 2026-10-26).
    # Retired IDs (mixtral-8x7b-32768, llama-3.2-*preview*, gemma2-9b-it,
    # qwen-2.5-32b/coder-32b) removed — they 404 on the API now.
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

OLLAMA_DEFAULTS = [
    "deepseek-r1:1.5b",
    "llama3.2:latest",
    "qwen2.5:7b",
    "tinyllama:latest",
]

# Shipped rule flavors (app/rules/flavors/). Persona keys from profiles.yml
# (senior_dev, prompt_engineer, …) and UI intents (concise, …) are NOT rule
# flavors — mapping them through here prevents silently running with
# base-rules-only.
KNOWN_FLAVORS = ("technical", "creative")


def _resolve_flavor(flavor: str) -> str:
    return flavor if flavor in KNOWN_FLAVORS else "technical"


def _build_architect(model: str, groq_api_key: Optional[str] = None):
    """
    Factory: returns the right Architect for the model string.
    """
    is_groq_pattern = model in GROQ_MODELS or model.startswith(
        ("llama-3", "mixtral", "gemma", "qwen-2.5", "openai/", "qwen/", "moonshotai/")
    )

    if is_groq_pattern:
        key = groq_api_key or settings.GROQ_API_KEY
        if key:
            logger.info("Using GroqArchitect with model: %s", model)
            return GroqArchitect(model_name=model, api_key=key)
        logger.warning(
            "Model '%s' looks like a Groq model but no API key is set. "
            "Falling back to Ollama with this model name.",
            model,
        )

    logger.info("Using OllamaArchitect with model: %s", model)
    return OllamaArchitect(model_name=model)


async def run_refinement(
    user_input: str,
    model: str = "deepseek-r1:1.5b",
    flavor: str = "technical",
    groq_api_key: Optional[str] = None,
    max_iterations: int = 3,
    profile_key: str = "",
) -> Dict[str, Any]:
    """
    Runs the PromptRefinementPipeline and returns a simplified result.
    Core function behind POST /generate and POST /optimize.
    """
    architect = _build_architect(model, groq_api_key)
    linter = PromptLinter()
    spec_validator = SpecValidator()
    mask = MaskService()

    config = {
        "flavor": _resolve_flavor(flavor),
        "max_iterations": max_iterations,
        "token_budget": 4000,
        "service_key": settings.SYSTEM_KEY,
        "model_profile": ModelProfileService().resolve(model),
        "rules": RuleLoader.load_rules(flavor),
    }

    pipeline = PromptRefinementPipeline(
        architect, linter, spec_validator, mask, config
    )

    result = await pipeline.process(
        user_input=user_input,
        template_id="default",
        requester={"id": "rest-api", "role": "gui_user", "profile": profile_key},
    )

    final_output = result.get("final_output") or {}
    success_gate = result.get("success_gate") or {}

    return {
        "response": final_output.get("rendered_prompt", ""),
        "success": bool(success_gate.get("passed")),
        "iterations": success_gate.get("iterations_used", 0),
        "token_usage": final_output.get("token_usage", {}),
        "audit_tags": result.get("audit_tags", []),
        "full_trace": result,
    }


async def get_available_models() -> List[Dict[str, Any]]:
    """Combined Ollama + Groq model list; never empty."""
    models: List[Dict[str, Any]] = []

    if settings.OLLAMA_ONLINE:
        try:
            import ollama

            response = await ollama.AsyncClient(host=settings.OLLAMA_HOST).list()
            ollama_models = [
                {
                    "id": model_id,
                    "provider": "ollama",
                    "requires_api_key": False,
                }
                for model_id in _extract_models(response)
            ]
            models.extend(ollama_models)
            logger.info("Found %s local Ollama models", len(ollama_models))
        except Exception as exc:
            logger.warning("Could not list Ollama models: %s", exc)

    groq_info = [
        {"id": m, "provider": "groq", "requires_api_key": True} for m in GROQ_MODELS
    ]
    models.extend(groq_info)

    if not models:
        defaults = [
            {"id": m, "provider": "ollama", "requires_api_key": False}
            for m in OLLAMA_DEFAULTS
        ]
        models = defaults + groq_info
        logger.warning("No models detected, returning defaults")

    seen = set()
    unique: List[Dict[str, Any]] = []
    for item in models:
        mid = item["id"]
        if mid not in seen:
            seen.add(mid)
            unique.append(item)
    return unique


def get_profiles() -> List[Dict[str, str]]:
    import yaml

    try:
        with open(settings.PROFILES_PATH, "r") as handle:
            data = yaml.safe_load(handle)
    except Exception as exc:
        logger.error("Failed to load profiles: %s", exc)
        return []

    profiles = []
    for key, value in (data or {}).items():
        if key == "visual_presets":
            continue
        if isinstance(value, dict) and "name" in value:
            profiles.append(
                {
                    "key": key,
                    "name": value["name"],
                    "description": value.get("description", ""),
                }
            )
    return profiles


def get_library() -> List[Dict[str, Any]]:
    try:
        rows = list_prompts(limit=1000)
        return [parse_prompt_row(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to load library: %s", exc)
        return []


def get_presets(model_id: str = "nano-banana-pro") -> List[Dict[str, Any]]:
    import yaml

    try:
        with open(settings.PROFILES_PATH, "r") as handle:
            data = yaml.safe_load(handle)
    except Exception as exc:
        logger.error("Failed to load profiles: %s", exc)
        return []

    visual = (data or {}).get("visual_presets", {})
    model_presets = visual.get(model_id, visual.get("nano-banana-pro", {}))
    return model_presets.get("presets", [])


def compile_visual(request: Dict[str, str]) -> str:
    parts = []
    for label, key in (
        ("Subject", "subject"),
        ("Environment", "environment"),
        ("Lighting", "lighting"),
        ("Camera", "camera"),
        ("Style", "render_style"),
        ("Text", "text_content"),
    ):
        value = request.get(key, "")
        if value:
            parts.append(f"{label}: {value}")
    return "\n".join(parts) if parts else "No visual components provided."

"""
API Router — All REST endpoints for the Prompt Architect frontend.

Endpoints:
  POST /generate      — Main prompt generation via Kayab pipeline
  GET  /models        — List available models (Ollama + Groq)
  GET  /profiles      — List persona profiles from profiles.yml
  GET  /library       — List saved prompts from SQLite
  POST /optimize      — Quick optimization via Kayab pipeline
  GET  /presets       — Visual presets by model ID
  POST /compile-visual — Compile visual prompt components
  GET  /vital-signs   — System health metrics (CPU, RAM, GPU)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from .config import settings
from .models import (
    GenerateRequest,
    GenerateResponse,
    OptimizeRequest,
    OptimizeResponse,
    VisualPromptRequest,
)
from .mcp_adapter import (
    run_refinement,
    get_available_models,
    get_profiles,
    get_library,
    get_presets,
    compile_visual,
    GROQ_MODELS,
)
from .hal import get_system_metrics, determine_tier

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    x_groq_api_key: Optional[str] = Header(None),
):
    """
    Main endpoint: generates a refined prompt using the Kayab pipeline.

    Accepts X-Groq-Api-Key header to override the configured key.
    Returns the rendered prompt text in the 'response' field.
    """
    groq_key = x_groq_api_key or settings.GROQ_API_KEY

    if request.model in GROQ_MODELS and not groq_key:
        raise HTTPException(
            status_code=400,
            detail=f"Groq API key required for model '{request.model}'. Set it in settings or send X-Groq-Api-Key header.",
        )

    try:
        result = await run_refinement(
            user_input=request.user_input,
            model=request.model,
            flavor=request.profile_key or "technical",
            groq_api_key=groq_key,
            profile_key=request.profile_key,
        )

        response_text = (result.get("response") or "").strip()
        success = bool(result.get("success"))
        full_trace = result.get("full_trace") or {}
        success_gate = full_trace.get("success_gate") or {}
        reason = success_gate.get("reason") or full_trace.get("reason")
        signature = full_trace.get("integrity_signature")

        if not success and not response_text:
            logger.warning("Generation failed with empty output: %s", reason)
            raise HTTPException(
                status_code=422,
                detail=reason or "Refinement failed with no usable output",
            )

        if not success:
            logger.warning(
                "Generation soft-fail (returning partial output): %s", reason
            )

        return GenerateResponse(
            response=response_text,
            success=success,
            reason=reason,
            iterations=int(result.get("iterations") or 0),
            integrity_signature=signature,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/models")
async def list_models():
    """
    Returns a list of available models (Ollama local + Groq cloud).
    Never returns an empty list — falls back to defaults.
    """
    models = await get_available_models()
    return {"models": models}


@router.get("/profiles")
async def list_profiles():
    """
    Returns all persona profiles from profiles.yml.
    """
    profiles = get_profiles()
    return {"profiles": profiles}


@router.get("/library")
async def get_prompt_library():
    """
    Returns all saved prompts from the SQLite library.
    """
    library = get_library()
    return {"library": library}


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize(
    request: OptimizeRequest,
    x_groq_api_key: Optional[str] = Header(None),
):
    """
    Quick optimization endpoint — runs the Kayab pipeline with intent context.
    """
    groq_key = x_groq_api_key or settings.GROQ_API_KEY
    model = request.target_model or "deepseek-r1:1.5b"

    try:
        result = await run_refinement(
            user_input=f"Intent: {request.intent}\n\nPrompt: {request.prompt}",
            model=model,
            flavor="technical",
            groq_api_key=groq_key,
            max_iterations=3,
        )

        tier_id, tier_name = determine_tier()

        response_text = (result.get("response") or "").strip()
        if not result.get("success") and not response_text:
            raise HTTPException(
                status_code=422,
                detail="Optimization failed with no usable output",
            )

        return OptimizeResponse(
            optimized_prompt=response_text,
            model_profile_used=model,
            operational_tier=tier_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get("/presets")
async def get_visual_presets(model_id: str = "nano-banana-pro"):
    """
    Returns visual prompt presets for the specified model.
    """
    presets = get_presets(model_id)
    return {"presets": presets, "model_id": model_id}


@router.post("/compile-visual")
async def compile_visual_prompt(request: VisualPromptRequest):
    """
    Compiles visual prompt components into a single prompt string.
    """
    compiled = compile_visual(
        {
            "subject": request.subject,
            "text_content": request.text_content,
            "environment": request.environment,
            "lighting": request.lighting,
            "camera": request.camera,
            "render_style": request.render_style,
        }
    )
    return {"compiled_prompt": compiled}


@router.get("/vital-signs")
async def get_vital_signs():
    """
    Returns current system health metrics for the PID controller and UI display.
    Polled every 800ms by SystemVitals.svelte.
    """
    try:
        metrics = get_system_metrics()
        tier_id, tier_name = determine_tier()

        return {
            "cpu_percent": metrics["cpu_percent"],
            "ram_percent": metrics["ram_percent"],
            "temperature": metrics["temperature"],
            "gpu_load": metrics["gpu_load"],
            "tier_id": tier_id,
            "tier_name": tier_name,
            "ollama_online": settings.OLLAMA_ONLINE,
            "groq_configured": bool(settings.GROQ_API_KEY),
        }
    except Exception as e:
        logger.error(f"Vital signs read failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sensor read failed: {str(e)}")

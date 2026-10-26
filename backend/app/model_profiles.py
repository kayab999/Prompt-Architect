"""
Model profile service — per-family LLM behavior for the refinement pipeline.

Resolves a concrete model ID (e.g. "deepseek-r1-distill-qwen-7b-q4_k_m:latest")
to a ModelProfile using: exact model entry → family pattern → generic defaults.
Profiles are data (backend/model_profiles.yml), sourced from the official model
cards; community fine-tunes are marked experimental.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelProfile:
    model_id: str
    family: str = "generic"
    description: str = ""
    use_system_role: bool = True
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: Optional[int] = None
    num_ctx: int = 8192
    num_predict: int = 2048
    stop: List[str] = field(default_factory=list)
    quirks: List[str] = field(default_factory=list)
    extra_system_directives: str = ""
    experimental: bool = False

    def ollama_options(self) -> Dict[str, Any]:
        """Sampling options for the Ollama chat API."""
        opts: Dict[str, Any] = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }
        if self.top_k is not None:
            opts["top_k"] = self.top_k
        if self.stop:
            opts["stop"] = list(self.stop)
        return opts

    def groq_options(self) -> Dict[str, Any]:
        """Sampling parameters for the Groq chat API."""
        opts: Dict[str, Any] = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.num_predict,
        }
        if self.stop:
            opts["stop"] = list(self.stop)
        return opts


class ModelProfileService:
    """Loads model_profiles.yml and resolves per-model profiles."""

    FAMILY_PATTERNS = [
        (r"deepseek-r1", "deepseek_r1"),
        (r"distill.*deepseek|deepseek.*distill", "deepseek_r1"),
        (r"qwen2\.5-coder", "qwen25_coder"),
        (r"qwen2\.5", "qwen25"),
        (r"qwen3", "qwen3"),
        (r"smollm2", "smollm2"),
        (r"bonsai", "bonsai"),
        (r"fable", "fable"),
        (r"synapse-deepseek", "deepseek_ft"),
        (r"llama3", "llama3"),
    ]

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else Path(settings.MODEL_PROFILES_PATH)
        self._cache: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        if self._cache is None:
            try:
                with open(self.path, "rb") as handle:
                    self._cache = yaml.safe_load(handle) or {}
            except Exception as exc:
                logger.warning(
                    "model_profiles.yml unavailable (%s); using generic defaults", exc
                )
                self._cache = {}
        return self._cache

    def _family_for(self, model_id: str) -> str:
        for pattern, family in self.FAMILY_PATTERNS:
            if re.search(pattern, model_id, flags=re.IGNORECASE):
                return family
        return "generic"

    def resolve(self, model_id: str) -> ModelProfile:
        """Exact model entry → declared family → pattern match → generic."""
        data = self._load()
        defaults = dict(data.get("defaults") or {})
        families = data.get("families") or {}
        models = data.get("models") or {}

        family_name = self._family_for(model_id)
        model_entry = models.get(model_id) or {}
        family_name = model_entry.get("family", family_name)
        family_cfg = families.get(family_name) or {}

        merged = {**defaults, **family_cfg, **model_entry}
        merged.pop("family", None)

        top_k = merged.get("top_k")
        profile = ModelProfile(
            model_id=model_id,
            family=family_name,
            description=str(merged.get("description", "")),
            use_system_role=bool(merged.get("use_system_role", True)),
            temperature=float(merged.get("temperature", 0.7)),
            top_p=float(merged.get("top_p", 0.9)),
            top_k=int(top_k) if top_k is not None else None,
            num_ctx=int(merged.get("num_ctx", 8192)),
            num_predict=int(merged.get("num_predict", 2048)),
            stop=[str(s) for s in (merged.get("stop") or [])],
            quirks=[str(q) for q in (merged.get("quirks") or [])],
            extra_system_directives=str(merged.get("extra_system_directives", "") or ""),
            experimental=bool(merged.get("experimental", False)),
        )
        return clamp_to_hardware(profile)


def clamp_to_hardware(profile: ModelProfile) -> ModelProfile:
    """Clamp KV-cache-related options to what the machine can actually hold.

    Ollama declines model loads (HTTP 500) when weights + KV cache do not fit;
    7B-class models are unloadable on 8 GB machines. Caps: <=8 GB → 2048 ctx /
    1024 out; <=16 GB → 4096 ctx / 2048 out; larger machines keep YAML values.
    """
    caps = {"num_ctx": 8192, "num_predict": 4096}
    try:
        import psutil

        total_gb = psutil.virtual_memory().total / (1024**3)
    except Exception:  # psutil unavailable → keep YAML values
        return profile
    if total_gb <= 8:
        caps = {"num_ctx": 2048, "num_predict": 1024}
    elif total_gb <= 16:
        caps = {"num_ctx": 4096, "num_predict": 2048}
    profile.num_ctx = min(profile.num_ctx, caps["num_ctx"])
    profile.num_predict = min(profile.num_predict, caps["num_predict"])
    return profile

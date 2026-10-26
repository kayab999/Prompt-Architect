"""Ollama-backed Architect implementation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .architect import Architect
from .config import settings

logger = logging.getLogger(__name__)


class OllamaArchitect(Architect):
    """Wraps the Ollama async client for draft generation."""

    def __init__(
        self,
        model_name: str = "llama3.2:latest",
        host: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(model_name=model_name)
        self.host = host or settings.OLLAMA_HOST
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT
        self._client = None

    def _get_client(self):
        if self._client is None:
            import ollama

            # Host only — let the SDK manage HTTP timeouts/defaults
            self._client = ollama.AsyncClient(host=self.host)
        return self._client

    async def generate(self, context: str) -> Dict[str, Any]:
        try:
            import asyncio

            client = self._get_client()
            response = await asyncio.wait_for(
                client.chat(
                    model=self.model_id,
                    messages=[{"role": "user", "content": context}],
                ),
                timeout=self.timeout,
            )
            # SDK returns object or dict depending on version
            message = getattr(response, "message", None)
            if message is not None:
                text = getattr(message, "content", None) or ""
            elif isinstance(response, dict):
                text = (response.get("message") or {}).get("content") or ""
            else:
                text = str(response)

            if not str(text).strip():
                return {
                    "raw_text": "",
                    "token_usage": {"prompt": 0, "completion": 0, "total": 0},
                    "confidence": 0.0,
                    "error": "Ollama returned empty content",
                }

            prompt_eval = getattr(response, "prompt_eval_count", None)
            eval_count = getattr(response, "eval_count", None)
            if isinstance(response, dict):
                prompt_eval = response.get("prompt_eval_count", prompt_eval)
                eval_count = response.get("eval_count", eval_count)

            prompt_tokens = int(prompt_eval or max(len(context) // 4, 0))
            completion_tokens = int(eval_count or max(len(text) // 4, 0))

            return {
                "raw_text": text,
                "token_usage": {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": prompt_tokens + completion_tokens,
                },
                "confidence": 0.85,
                "error": None,
            }
        except Exception as exc:
            logger.error("Ollama generation failed: %s: %s", type(exc).__name__, exc)
            return {
                "raw_text": "",
                "token_usage": {"prompt": 0, "completion": 0, "total": 0},
                "confidence": 0.0,
                "error": f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__,
            }

    async def list_models(self) -> List[str]:
        try:
            client = self._get_client()
            response = await client.list()
            models = _extract_models(response)
            return [m for m in models if m]
        except Exception as exc:
            logger.warning("Ollama list_models failed: %s", exc)
            return []

    async def health_check(self) -> bool:
        try:
            models = await self.list_models()
            return True if models is not None else False
        except Exception:
            return False


def _extract_models(response: Any) -> List[str]:
    """Normalize Ollama list() response across SDK versions."""
    raw_models = getattr(response, "models", None)
    if raw_models is None and isinstance(response, dict):
        raw_models = response.get("models", [])
    if not raw_models:
        return []

    ids: List[str] = []
    for item in raw_models:
        model_id = _model_id_from_entry(item)
        if model_id:
            ids.append(model_id)
    return ids


def _model_id_from_entry(item: Any) -> Optional[str]:
    if item is None:
        return None
    if isinstance(item, str):
        return item
    model_id = getattr(item, "model", None) or getattr(item, "name", None)
    if model_id:
        return str(model_id)
    if isinstance(item, dict):
        return item.get("model") or item.get("name")
    # Mapping-like SDK objects
    try:
        return item["model"]  # type: ignore[index]
    except Exception:
        pass
    try:
        return item["name"]  # type: ignore[index]
    except Exception:
        return None

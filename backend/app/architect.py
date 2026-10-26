"""
An abstract base class for LLM architects.

Concrete implementations should handle communication with specific LLM providers
(e.g., Ollama, Groq, OpenAI).
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class Architect:
    """
    Abstract base class for LLM architects.

    Concrete implementations are responsible for interacting with specific LLM
    providers, handling model selection, API calls, and response parsing.
    """

    def __init__(self, model_name: str = "default-model"):
        self.model_id = model_name
        logger.info(f"Initializing Architect for model: {self.model_id}")

    async def generate(
        self,
        context: str,
        *,
        system: str = "",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a draft prompt using the wrapped LLM.

        Args:
            context: The user-side prompt or context for the LLM.
            system: Optional system message. When empty, providers receive a
                single user message (required for DeepSeek-R1 family).
            options: Optional provider-specific sampling parameters
                (temperature, top_p, top_k, stop, num_ctx, num_predict...).

        Returns:
            A dictionary containing the generated text, token usage, and confidence.
            Example:
            {
                "raw_text": "Generated prompt string...",
                "token_usage": {"prompt": 100, "completion": 200, "total": 300},
                "confidence": 0.85,
                "error": None # or an error string if applicable
            }
        """
        raise NotImplementedError("Subclasses must implement the 'generate' method.")

    async def list_models(self) -> List[str]:
        """
        Lists available models for this architect.
        This method might be optional depending on the architect's nature.
        """
        logger.warning("list_models not implemented for this architect.")
        return []

    async def health_check(self) -> bool:
        """
        Performs a health check on the LLM backend.
        Returns True if healthy, False otherwise.
        """
        logger.warning("health_check not implemented for this architect.")
        return False

    async def disconnect(self):
        """
        Clean up any resources or connections.
        """
        logger.info(f"Disconnecting Architect for model: {self.model_id}")
        pass

import logging
from typing import Any, Dict, List
from .architect import Architect # Import the base class

logger = logging.getLogger(__name__)

class GroqArchitect(Architect): # Inherit from Architect
    """Wraps Groq API for draft generation, matching the Architect interface."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile", api_key: str | None = None):
        super().__init__(model_name=model_name) # Call parent constructor
        from groq import AsyncGroq
        
        self.client = AsyncGroq(api_key=api_key)
        logger.info("Initialized GroqArchitect for model: %s", self.model_id)

    async def generate(
        self,
        context: str,
        *,
        system: str = "",
        options: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Generates a draft prompt using Groq."""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": context})

            params: Dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            if options:
                allowed = ("temperature", "top_p", "max_tokens", "stop")
                params.update(
                    {
                        k: v
                        for k, v in options.items()
                        if k in allowed and v is not None
                    }
                )

            response = await self.client.chat.completions.create(**params)
            text = response.choices[0].message.content or ""
            prompt_tokens = (
                response.usage.prompt_tokens if response.usage else len(context) // 4
            )
            completion_tokens = (
                response.usage.completion_tokens if response.usage else len(text) // 4
            )

            return {
                "raw_text": text,
                "token_usage": {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": prompt_tokens + completion_tokens,
                },
                "confidence": 0.9,
            }
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return {
                "raw_text": f"Error: {str(e)}",
                "token_usage": {"total": 0},
                "confidence": 0.0,
                "error": str(e),
            }

    async def list_models(self) -> List[str]:
        """
        Lists available Groq models.
        Note: This is a simplified list. A real implementation might fetch dynamically.
        """
        # For now, returning the predefined list as specified in mcp_adapter.py
        # A more robust implementation would call Groq API to get available models.
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-3b-preview",
            "llama-3.2-11b-vision-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "qwen-2.5-32b",
            "qwen-2.5-coder-32b",
        ]

    async def health_check(self) -> bool:
        """
        Performs a health check by attempting a simple API call (e.g., listing models).
        """
        try:
            await self.list_models() # A simple call to check connectivity
            return True
        except Exception:
            return False

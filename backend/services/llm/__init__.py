import os
import logging
from services.llm.base import LLMProvider
from services.llm.ollama import OllamaProvider


def get_llm_provider() -> LLMProvider:
    """Return an LLM provider instance.

    Preference is controlled by `LLM_PROVIDER` env var (e.g. "gemini" or "ollama").
    If the preferred provider fails to initialise, fall back to Ollama.
    """
    logger = logging.getLogger("vini.llm")
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        try:
            from services.llm.gemini import GeminiProvider

            return GeminiProvider()
        except Exception as e:
            logger.warning(f"Failed to initialise Gemini provider: {e}. Falling back to Ollama.")
            return OllamaProvider()

    if provider == "ollama":
        return OllamaProvider()

    logger.warning(f"Unknown LLM_PROVIDER '{provider}', defaulting to Ollama.")
    return OllamaProvider()
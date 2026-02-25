import os
from services.llm.base import LLMProvider
from services.llm.ollama import OllamaProvider


def get_llm_provider() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "ollama")

    if provider == "ollama":
        return OllamaProvider()

    if provider == "gemini":
        from services.llm.gemini import GeminiProvider
        return GeminiProvider()

    raise ValueError(f"Unknown LLM provider: {provider}")
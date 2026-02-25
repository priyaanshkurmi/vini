from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMProvider(ABC):

    @abstractmethod
    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream tokens from the LLM one chunk at a time."""
        ...
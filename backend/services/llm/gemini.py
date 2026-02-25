import os
import asyncio
from typing import AsyncGenerator
from services.llm.base import LLMProvider


class GeminiProvider(LLMProvider):

    def __init__(self):
        import google.genai as genai
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model  = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        import google.genai as genai

        # Run the entire Gemini call in a thread and return full text
        def _get_full_response() -> str:
            full = ""
            for chunk in self.client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
            ):
                if chunk.text:
                    full += chunk.text
            return full

        full_response = await asyncio.to_thread(_get_full_response)

        # Yield in small word-sized pieces so streaming feels natural
        words = full_response.split(" ")
        for i, word in enumerate(words):
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word
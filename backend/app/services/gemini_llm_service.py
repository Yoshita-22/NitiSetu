import json
import logging
from typing import Any, Dict, Optional
from app.core.config import settings

logger = logging.getLogger("nitisetu.gemini_llm")


class GeminiLLMService:
    """Service client for Google Gemini Multilingual LLM."""

    def __init__(self):
        raw_key = settings.GEMINI_API_KEY or ""
        self.api_key = raw_key.strip("'\" \t\r\n") if raw_key else None
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google.genai Client for LLM: {str(e)}")
        return self._client

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[str]:
        """Generate multilingual text response using Gemini LLM."""
        if not prompt.strip():
            return None

        client = self._get_client()
        if not client:
            return None

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=0.1,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text if response else None
        except Exception as e:
            logger.error(f"Gemini LLM text generation error: {str(e)}")
            return None

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate structured JSON response using Gemini LLM."""
        text = await self.generate_text(prompt, system_instruction)
        if not text:
            return None

        try:
            # Strip markdown code blocks if wrapped in ```json
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                if cleaned.endswith("```"):
                    cleaned = cleaned.rsplit("```", 1)[0]
            return json.loads(cleaned.strip())
        except Exception as e:
            logger.warning(f"Failed to parse Gemini response as JSON: {str(e)}")
            return None


gemini_llm_service = GeminiLLMService()

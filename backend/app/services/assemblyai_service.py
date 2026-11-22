import asyncio
import logging
from typing import Optional
import httpx
from app.core.config import settings
from app.schemas.voice_schemas import SpeechToTextResponse

logger = logging.getLogger("nitisetu.assemblyai_service")

# Mapping of generic language codes to AssemblyAI language codes
ASSEMBLYAI_LANG_MAP = {
    "en": "en",
    "en-in": "en",
    "hi": "hi",
    "hi-in": "hi",
    "te": "te",
    "te-in": "te",
}


class AssemblyAIService:
    """Service client for AssemblyAI Multilingual Speech-to-Text."""

    def __init__(self):
        raw_key = settings.ASSEMBLYAI_API_KEY or ""
        self.api_key = raw_key.strip("'\" \t\r\n") if raw_key else None
        self.base_url = settings.ASSEMBLYAI_BASE_URL.rstrip("/")
        self.timeout = settings.ASSEMBLYAI_TIMEOUT_SECONDS

    def normalize_language_code(self, lang: Optional[str]) -> Optional[str]:
        """Map language abbreviation to AssemblyAI supported language code."""
        if not lang or lang.lower() == "unknown":
            return None
        norm = lang.lower().strip()
        return ASSEMBLYAI_LANG_MAP.get(norm, None)

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: Optional[str] = "unknown",
    ) -> SpeechToTextResponse:
        """Transcribe speech audio using AssemblyAI Multilingual STT API."""
        if not audio_bytes:
            return SpeechToTextResponse(
                transcript="",
                language_code=language_code or "unknown",
                success=False,
                error="Empty audio content provided.",
            )

        norm_lang = self.normalize_language_code(language_code)

        # Fallback when no AssemblyAI API key configured
        if not self.api_key:
            logger.warning("ASSEMBLYAI_API_KEY not configured. Returning local development transcript.")
            return SpeechToTextResponse(
                transcript="Namaste! This is a simulated transcription from AssemblyAI. Please configure ASSEMBLYAI_API_KEY in backend/.env for live multilingual STT.",
                language_code=norm_lang or "en",
                success=True,
            )

        headers = {
            "authorization": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Upload audio file binary to AssemblyAI CDN
                upload_res = await client.post(
                    f"{self.base_url}/upload",
                    headers=headers,
                    content=audio_bytes,
                )
                upload_res.raise_for_status()
                upload_url = upload_res.json().get("upload_url")
                if not upload_url:
                    return SpeechToTextResponse(
                        transcript="",
                        language_code=norm_lang or "unknown",
                        success=False,
                        error="AssemblyAI audio upload failed to return URL.",
                    )

                # Step 2: Request transcription with Universal model for multilingual support (Telugu, Hindi, English)
                transcript_payload = {
                    "audio_url": upload_url,
                    "speech_model": "universal",
                }
                if norm_lang:
                    transcript_payload["language_code"] = norm_lang
                else:
                    transcript_payload["language_detection"] = True

                transcript_res = await client.post(
                    f"{self.base_url}/transcript",
                    headers={**headers, "content-type": "application/json"},
                    json=transcript_payload,
                )
                transcript_res.raise_for_status()
                transcript_data = transcript_res.json()
                transcript_id = transcript_data.get("id")

                if not transcript_id:
                    return SpeechToTextResponse(
                        transcript="",
                        language_code=norm_lang or "unknown",
                        success=False,
                        error="Failed to start AssemblyAI transcription job.",
                    )

                # Step 3: Poll for transcription completion (max 20 seconds, checking every 1s)
                poll_url = f"{self.base_url}/transcript/{transcript_id}"
                for _ in range(20):
                    await asyncio.sleep(1.0)
                    poll_res = await client.get(poll_url, headers=headers)
                    if poll_res.status_code == 200:
                        poll_data = poll_res.json()
                        job_status = poll_data.get("status")

                        if job_status == "completed":
                            text = poll_data.get("text", "").strip()
                            detected_lang = poll_data.get("language_code", norm_lang or "en")
                            return SpeechToTextResponse(
                                transcript=text,
                                language_code=detected_lang,
                                success=True,
                            )
                        elif job_status == "error":
                            error_msg = poll_data.get("error", "Transcription error occurred")
                            return SpeechToTextResponse(
                                transcript="",
                                language_code=norm_lang or "unknown",
                                success=False,
                                error=error_msg,
                            )

                return SpeechToTextResponse(
                    transcript="",
                    language_code=norm_lang or "unknown",
                    success=False,
                    error="AssemblyAI transcription timed out.",
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"AssemblyAI HTTP error {e.response.status_code}: {e.response.text}")
            return SpeechToTextResponse(
                transcript="",
                language_code=norm_lang or "unknown",
                success=False,
                error=f"AssemblyAI HTTP error {e.response.status_code}: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"AssemblyAI connection error: {str(e)}")
            return SpeechToTextResponse(
                transcript="",
                language_code=norm_lang or "unknown",
                success=False,
                error=str(e),
            )


assemblyai_service = AssemblyAIService()

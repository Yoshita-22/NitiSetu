import base64
import logging
import re
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.schemas.voice_schemas import SpeechToTextResponse, TextToSpeechResponse

logger = logging.getLogger("nitisetu.sarvam_service")

# Mapping of generic codes to Sarvam BCP-47 language codes
SARVAM_LANG_MAP = {
    "en": "en-IN",
    "en-in": "en-IN",
    "te": "te-IN",
    "te-in": "te-IN",
    "hi": "hi-IN",
    "hi-in": "hi-IN",
}

# Default speaker personas for Sarvam Bulbul:v3
DEFAULT_SPEAKERS = {
    "en-IN": "kavya",
    "te-IN": "kavitha",
    "hi-IN": "kavya",
}


def clean_markdown_for_speech(text: str, max_chars: int = 500) -> str:
    """Strip markdown formatting and truncate text for natural speech synthesis."""
    if not text:
        return ""

    # Remove code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    # Remove inline code
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    # Convert markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove bold/italic markers
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    # Remove markdown headers (#, ##, ###)
    cleaned = re.sub(r"^\s*#+\s*", "", cleaned, flags=re.MULTILINE)
    # Remove bullet markers
    cleaned = re.sub(r"^\s*[\*\-\+]\s+", "", cleaned, flags=re.MULTILINE)
    # Replace multiple newlines or spaces with single space
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Sarvam Bulbul has a 500 character limit per input chunk
    if len(cleaned) > max_chars:
        # Truncate at sentence boundary or word boundary
        truncated = cleaned[:max_chars]
        last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
        if last_punct > max_chars // 2:
            cleaned = truncated[: last_punct + 1]
        else:
            cleaned = truncated[: truncated.rfind(" ")] + "..."

    return cleaned


class SarvamService:
    """Service client for Sarvam AI Speech-to-Text (Saarika) and Text-to-Speech (Bulbul)."""

    def __init__(self):
        raw_key = settings.SARVAM_API_KEY or ""
        self.api_key = raw_key.strip("'\" \t\r\n") if raw_key else None
        self.base_url = settings.SARVAM_BASE_URL.rstrip("/")
        self.stt_model = settings.SARVAM_STT_MODEL
        self.tts_model = settings.SARVAM_TTS_MODEL
        self.timeout = settings.SARVAM_TIMEOUT_SECONDS

    def normalize_language_code(self, lang: Optional[str]) -> str:
        """Map language abbreviation or BCP-47 tag to Sarvam-supported code."""
        if not lang or lang.lower() == "unknown":
            return "unknown"
        norm = lang.lower().strip()
        return SARVAM_LANG_MAP.get(norm, "en-IN")

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: Optional[str] = "unknown",
    ) -> SpeechToTextResponse:
        """Transcribe citizen audio using Sarvam Saarika STT API."""
        if not audio_bytes:
            return SpeechToTextResponse(
                transcript="",
                language_code=language_code or "unknown",
                success=False,
            )

        norm_lang = self.normalize_language_code(language_code)

        # Fallback when no Sarvam API key configured
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not configured. Returning local development transcript.")
            return SpeechToTextResponse(
                transcript="Namaste! This is a simulated transcription. Please configure SARVAM_API_KEY in backend/.env for live Sarvam STT.",
                language_code=norm_lang if norm_lang != "unknown" else "en-IN",
                success=True,
            )

        endpoint = f"{self.base_url}/speech-to-text"
        headers = {
            "api-subscription-key": self.api_key,
        }

        data = {
            "model": self.stt_model,
        }
        if norm_lang != "unknown":
            data["language_code"] = norm_lang

        files = {
            "file": (filename, audio_bytes, content_type),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, headers=headers, data=data, files=files)
                response.raise_for_status()
                res_data = response.json()

                transcript = res_data.get("transcript", "").strip()
                detected_lang = res_data.get("language_code", norm_lang)

                return SpeechToTextResponse(
                    transcript=transcript,
                    language_code=detected_lang,
                    success=True,
                )
        except httpx.HTTPStatusError as e:
            err_msg = f"Sarvam STT error {e.response.status_code}"
            try:
                err_data = e.response.json()
                if "error" in err_data and "message" in err_data["error"]:
                    err_msg = err_data["error"]["message"]
            except Exception:
                err_msg = e.response.text or err_msg
            logger.error(f"Sarvam STT HTTP error {e.response.status_code}: {err_msg}")
            return SpeechToTextResponse(
                transcript="",
                language_code=norm_lang,
                success=False,
                error=err_msg,
            )
        except Exception as e:
            logger.error(f"Sarvam STT connection error: {str(e)}")
            return SpeechToTextResponse(
                transcript="",
                language_code=norm_lang,
                success=False,
                error=str(e),
            )

    async def text_to_speech(
        self,
        text: str,
        language_code: Optional[str] = "en-IN",
        speaker: Optional[str] = None,
    ) -> TextToSpeechResponse:
        """Synthesize plain text into speech using Sarvam Bulbul TTS API."""
        norm_lang = self.normalize_language_code(language_code)
        if norm_lang == "unknown":
            norm_lang = "en-IN"

        cleaned_text = clean_markdown_for_speech(text, max_chars=500)
        if not cleaned_text:
            return TextToSpeechResponse(
                audio_base64="",
                language_code=norm_lang,
                format="wav",
                success=False,
            )

        chosen_speaker = speaker or DEFAULT_SPEAKERS.get(norm_lang, settings.SARVAM_DEFAULT_SPEAKER)

        # Fallback when no Sarvam API key configured: return empty audio with success flag
        if not self.api_key:
            logger.warning("SARVAM_API_KEY not configured. Returning placeholder TTS response.")
            # 1 second of silent WAV base64 placeholder (RIFF header + silence)
            dummy_wav_base64 = "UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAP8A"
            return TextToSpeechResponse(
                audio_base64=dummy_wav_base64,
                language_code=norm_lang,
                format="wav",
                success=True,
            )

        endpoint = f"{self.base_url}/text-to-speech"
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": [cleaned_text],
            "target_language_code": norm_lang,
            "speaker": chosen_speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": self.tts_model,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                res_data = response.json()

                audios = res_data.get("audios", [])
                audio_base64 = audios[0] if audios else ""

                return TextToSpeechResponse(
                    audio_base64=audio_base64,
                    language_code=norm_lang,
                    format="wav",
                    success=bool(audio_base64),
                )
        except httpx.HTTPStatusError as e:
            err_msg = f"Sarvam TTS error {e.response.status_code}"
            try:
                err_data = e.response.json()
                if "error" in err_data and "message" in err_data["error"]:
                    err_msg = err_data["error"]["message"]
            except Exception:
                err_msg = e.response.text or err_msg
            logger.error(f"Sarvam TTS HTTP error {e.response.status_code}: {err_msg}")
            return TextToSpeechResponse(
                audio_base64="",
                language_code=norm_lang,
                format="wav",
                success=False,
                error=err_msg,
            )
        except Exception as e:
            logger.error(f"Sarvam TTS connection error: {str(e)}")
            return TextToSpeechResponse(
                audio_base64="",
                language_code=norm_lang,
                format="wav",
                success=False,
                error=str(e),
            )


sarvam_service = SarvamService()

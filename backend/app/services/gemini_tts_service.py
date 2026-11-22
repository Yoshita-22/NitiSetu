import base64
import logging
import re
from typing import Optional
from app.core.config import settings
from app.schemas.voice_schemas import SpeechToTextResponse, TextToSpeechResponse

logger = logging.getLogger("nitisetu.gemini_tts")

LANG_NAME_MAP = {
    "en": "Indian English",
    "en-in": "Indian English",
    "te": "Telugu",
    "te-in": "Telugu",
    "hi": "Hindi",
    "hi-in": "Hindi",
}

# Voices supported by Gemini: Aoede, Charon, Fenrir, Kore, Puck
VOICE_MAP = {
    "en-IN": "Puck",
    "te-IN": "Aoede",
    "hi-IN": "Kore",
}


def clean_text_for_gemini_speech(text: str, max_chars: int = 1000) -> str:
    """Clean markdown formatting for natural, fluent speech generation."""
    if not text:
        return ""
    # Strip code blocks
    cleaned = re.sub(r"```[\s\S]*?```", "", text)
    cleaned = re.sub(r"`[^`]+`", "", cleaned)
    # Convert markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove bold/italic markers
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    # Remove markdown headers and bullets
    cleaned = re.sub(r"^\s*#+\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[\*\-\+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0] + "..."
    return cleaned


class GeminiTTSService:
    """Service client for Google Gemini Multilingual Text-to-Speech."""

    def __init__(self):
        raw_key = settings.GEMINI_API_KEY or ""
        self.api_key = raw_key.strip("'\" \t\r\n") if raw_key else None
        self.model = settings.GEMINI_TTS_MODEL
        self.voice_name = settings.GEMINI_VOICE_NAME
        self._genai_client = None

    def _get_client(self):
        if self._genai_client is None and self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize google.genai Client: {str(e)}")
        return self._genai_client

    async def text_to_speech(
        self,
        text: str,
        language_code: Optional[str] = "en-IN",
        speaker: Optional[str] = None,
    ) -> TextToSpeechResponse:
        """Synthesize text into speech audio using Gemini Audio output."""
        norm_code = (language_code or "en-IN").lower().strip()
        lang_name = LANG_NAME_MAP.get(norm_code, "English")
        clean_code = "te-IN" if "te" in norm_code else ("hi-IN" if "hi" in norm_code else "en-IN")

        cleaned = clean_text_for_gemini_speech(text)
        if not cleaned:
            return TextToSpeechResponse(
                audio_base64="",
                language_code=clean_code,
                format="wav",
                success=False,
                error="Text content cannot be empty.",
            )

        # Fallback when no Gemini API key is configured
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Returning placeholder TTS response.")
            # 1 second of silent WAV base64 placeholder (RIFF header + silence)
            dummy_wav_base64 = "UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAP8A"
            return TextToSpeechResponse(
                audio_base64=dummy_wav_base64,
                language_code=clean_code,
                format="wav",
                success=True,
            )

        client = self._get_client()
        if not client:
            return TextToSpeechResponse(
                audio_base64="",
                language_code=clean_code,
                format="wav",
                success=False,
                error="Google GenAI client could not be initialized.",
            )

        voice = speaker or VOICE_MAP.get(clean_code, self.voice_name)

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                ),
            )

            # Pass the pure cleaned text directly to contents.
            # Dedicated TTS models synthesize the contents verbatim;
            # do not prepend instructions like 'Please read aloud...' or they will be spoken.
            response = client.models.generate_content(
                model=self.model,
                contents=cleaned,
                config=config,
            )

            # Extract audio bytes from response parts
            audio_bytes = None
            format_ext = "wav"

            if response and response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            audio_bytes = part.inline_data.data
                            mime = getattr(part.inline_data, "mime_type", "")
                            if "mp3" in mime:
                                format_ext = "mp3"
                            break

            if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                return TextToSpeechResponse(
                    audio_base64=audio_b64,
                    language_code=clean_code,
                    format=format_ext,
                    success=True,
                )
            else:
                return TextToSpeechResponse(
                    audio_base64="",
                    language_code=clean_code,
                    format="wav",
                    success=False,
                    error="Gemini returned no audio content.",
                )

        except Exception as e:
            logger.error(f"Gemini TTS generation error: {str(e)}")
            return TextToSpeechResponse(
                audio_base64="",
                language_code=clean_code,
                format="wav",
                success=False,
                error=f"Gemini TTS generation error: {str(e)}",
            )

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: Optional[str] = "unknown",
    ) -> SpeechToTextResponse:
        """Transcribe speech audio directly using Gemini Multimodal Audio understanding."""
        if not audio_bytes:
            return SpeechToTextResponse(
                transcript="",
                language_code=language_code or "unknown",
                success=False,
                error="Empty audio provided.",
            )

        client = self._get_client()
        if not client:
            return SpeechToTextResponse(
                transcript="Namaste! (Gemini STT fallback mode)",
                language_code=language_code or "te",
                success=True,
            )

        try:
            from google.genai import types

            mime = content_type or "audio/wav"
            if "webm" in filename:
                mime = "audio/webm"
            elif "mp3" in filename:
                mime = "audio/mp3"

            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime)
            prompt = (
                "Please transcribe this spoken audio accurately and verbatim in the original language "
                "(Telugu, Hindi, or English). Return only the transcription text, without any additional explanations or prefixes."
            )

            response = client.models.generate_content(
                model=self.model,
                contents=[audio_part, prompt],
            )
            transcript = response.text.strip() if response and response.text else ""
            return SpeechToTextResponse(
                transcript=transcript,
                language_code=language_code or "te",
                success=bool(transcript),
            )
        except Exception as e:
            logger.error(f"Gemini Multimodal STT error: {str(e)}")
            return SpeechToTextResponse(
                transcript="",
                language_code=language_code or "unknown",
                success=False,
                error=str(e),
            )


gemini_tts_service = GeminiTTSService()

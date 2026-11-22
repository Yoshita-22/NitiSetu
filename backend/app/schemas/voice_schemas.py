from typing import Optional
from pydantic import BaseModel, Field


class SpeechToTextResponse(BaseModel):
    """Structured response from Speech-to-Text conversion."""

    transcript: str = Field(..., description="Transcribed text from speech audio")
    language_code: Optional[str] = Field("unknown", description="Detected or requested language code (e.g., en-IN, te-IN, hi-IN)")
    success: bool = Field(True, description="Whether transcription succeeded")
    error: Optional[str] = Field(None, description="Error message if transcription failed")


class TextToSpeechRequest(BaseModel):
    """Payload to synthesize speech from text."""

    text: str = Field(..., min_length=1, description="Text content to be synthesized into speech")
    language_code: Optional[str] = Field("en-IN", description="Target language code: 'en-IN', 'te-IN', 'hi-IN', or language prefix 'en', 'te', 'hi'")
    speaker: Optional[str] = Field(None, description="Optional speaker voice persona (e.g. 'meera', 'pavithra', 'arvind', 'amartya')")


class TextToSpeechResponse(BaseModel):
    """Structured response containing synthesized audio data."""

    audio_base64: str = Field(..., description="Base64-encoded audio (WAV format)")
    language_code: str = Field(..., description="Language code used for synthesis")
    format: str = Field("wav", description="Audio container format")
    success: bool = Field(True, description="Whether synthesis succeeded")
    error: Optional[str] = Field(None, description="Error message if synthesis failed")

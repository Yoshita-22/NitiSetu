import logging
from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from app.core.config import settings
from app.schemas.voice_schemas import (
    SpeechToTextResponse,
    TextToSpeechRequest,
    TextToSpeechResponse,
)
from app.services.assemblyai_service import assemblyai_service
from app.services.gemini_tts_service import gemini_tts_service
from app.services.sarvam_service import sarvam_service

logger = logging.getLogger("nitisetu.voice_routes")

router = APIRouter()


@router.post(
    "/stt",
    response_model=SpeechToTextResponse,
    summary="Convert citizen speech to text using AssemblyAI (Multilingual)",
    description="Transcribes audio recorded from browser microphone using AssemblyAI Multilingual STT API.",
)
async def speech_to_text(
    file: UploadFile = File(..., description="Audio file recorded by user (wav, webm, mp3)"),
    language_code: Optional[str] = Query("unknown", description="Language hint: 'en', 'te', 'hi', or 'unknown'"),
) -> SpeechToTextResponse:
    """Handle speech-to-text audio upload and invoke AssemblyAI STT."""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty audio file provided.",
            )

        filename = file.filename or "recording.wav"
        content_type = file.content_type or "audio/wav"

        # Route to AssemblyAI or Gemini as primary multilingual STT provider
        if settings.ASSEMBLYAI_API_KEY:
            result = await assemblyai_service.speech_to_text(
                audio_bytes=content,
                filename=filename,
                content_type=content_type,
                language_code=language_code,
            )
        elif settings.GEMINI_API_KEY:
            result = await gemini_tts_service.speech_to_text(
                audio_bytes=content,
                filename=filename,
                content_type=content_type,
                language_code=language_code,
            )
        elif settings.SARVAM_API_KEY:
            result = await sarvam_service.speech_to_text(
                audio_bytes=content,
                filename=filename,
                content_type=content_type,
                language_code=language_code,
            )
        else:
            # AssemblyAI default fallback
            result = await assemblyai_service.speech_to_text(
                audio_bytes=content,
                filename=filename,
                content_type=content_type,
                language_code=language_code,
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in speech_to_text endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech transcription failed: {str(e)}",
        )


@router.post(
    "/tts",
    response_model=TextToSpeechResponse,
    summary="Synthesize speech audio from text using Google Gemini TTS (Multilingual)",
    description="Generates speech audio from text answers using Google Gemini Multilingual Audio generation.",
)
async def text_to_speech(
    payload: TextToSpeechRequest,
) -> TextToSpeechResponse:
    """Handle text-to-speech request and return base64 audio."""
    try:
        if not payload.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text content cannot be empty.",
            )

        # Route to Google Gemini as primary multilingual TTS provider
        if settings.GEMINI_API_KEY:
            result = await gemini_tts_service.text_to_speech(
                text=payload.text,
                language_code=payload.language_code,
                speaker=payload.speaker,
            )
        elif settings.SARVAM_API_KEY:
            result = await sarvam_service.text_to_speech(
                text=payload.text,
                language_code=payload.language_code,
                speaker=payload.speaker,
            )
        else:
            # Gemini default fallback
            result = await gemini_tts_service.text_to_speech(
                text=payload.text,
                language_code=payload.language_code,
                speaker=payload.speaker,
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text_to_speech endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech synthesis failed: {str(e)}",
        )

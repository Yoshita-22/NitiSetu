import io
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.assemblyai_service import assemblyai_service
from app.services.gemini_tts_service import (
    clean_text_for_gemini_speech,
    gemini_tts_service,
)
from app.services.sarvam_service import (
    clean_markdown_for_speech,
    sarvam_service,
)

client = TestClient(app)


def test_clean_markdown_for_speech():
    """Verify markdown tags, links, and code blocks are stripped for natural speech."""
    raw_markdown = """
    # Welfare Scheme: PM-KISAN
    **PM-KISAN** provides *financial support* to all landholding farmers.
    - Benefit: ₹6,000 per year
    - Official portal: [PM-Kisan Portal](https://pmkisan.gov.in)
    ```python
    print("code snippet")
    ```
    """
    cleaned = clean_markdown_for_speech(raw_markdown, max_chars=300)
    assert "#" not in cleaned
    assert "**" not in cleaned
    assert "https://" not in cleaned
    assert "code snippet" not in cleaned
    assert "PM-KISAN provides financial support" in cleaned
    assert "PM-Kisan Portal" in cleaned
    assert len(cleaned) <= 300


def test_clean_text_for_gemini_speech():
    """Verify Gemini speech text cleaner removes formatting."""
    raw_text = "### Section 498A\n**Cruelty** by husband or relatives. [Learn more](https://law.gov.in)"
    cleaned = clean_text_for_gemini_speech(raw_text)
    assert "###" not in cleaned
    assert "**" not in cleaned
    assert "Cruelty by husband or relatives" in cleaned
    assert "Learn more" in cleaned


def test_assemblyai_normalize_language():
    """Verify AssemblyAI language code normalization."""
    assert assemblyai_service.normalize_language_code("en") == "en"
    assert assemblyai_service.normalize_language_code("hi") == "hi"
    assert assemblyai_service.normalize_language_code("te") == "te"
    assert assemblyai_service.normalize_language_code("te-in") == "te"
    assert assemblyai_service.normalize_language_code("unknown") is None
    assert assemblyai_service.normalize_language_code(None) is None


def test_stt_endpoint_fallback():
    """Verify STT endpoint handles audio upload gracefully with AssemblyAI/fallback."""
    audio_content = b"RIFF....WAVEfmt ....data...."
    file_tuple = ("test_audio.wav", io.BytesIO(audio_content), "audio/wav")

    response = client.post(
        "/api/v1/voice/stt?language_code=te",
        files={"file": file_tuple},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "transcript" in data


def test_stt_endpoint_empty_file_rejected():
    """Verify STT rejects empty audio uploads with HTTP 400."""
    empty_tuple = ("empty.wav", io.BytesIO(b""), "audio/wav")
    response = client.post(
        "/api/v1/voice/stt",
        files={"file": empty_tuple},
    )
    assert response.status_code == 400
    assert "Empty audio" in response.json()["detail"]


def test_tts_endpoint_fallback():
    """Verify TTS endpoint generates speech base64 data using Gemini TTS."""
    payload = {
        "text": "Namaste! PM-KISAN gives eligible farmers ₹6,000 every year.",
        "language_code": "hi",
    }
    response = client.post("/api/v1/voice/tts", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["audio_base64"]) > 0
    assert data["language_code"] == "hi-IN"
    assert data["format"] == "wav"


def test_tts_endpoint_empty_text_rejected():
    """Verify TTS rejects empty text payload with HTTP 400."""
    payload = {"text": "   "}
    response = client.post("/api/v1/voice/tts", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_assemblyai_stt_mock_flow():
    """Verify AssemblyAI upload, transcript, and polling workflow."""
    upload_mock = AsyncMock()
    upload_mock.status_code = 200
    upload_mock.raise_for_status = lambda: None
    upload_mock.json = lambda: {"upload_url": "https://cdn.assemblyai.com/test_audio.wav"}

    transcript_mock = AsyncMock()
    transcript_mock.status_code = 200
    transcript_mock.raise_for_status = lambda: None
    transcript_mock.json = lambda: {"id": "test_job_123", "status": "queued"}

    poll_mock = AsyncMock()
    poll_mock.status_code = 200
    poll_mock.json = lambda: {
        "status": "completed",
        "text": "రైతు బంధు పథకం అర్హతలు ఏమిటి?",
        "language_code": "te",
    }

    with patch.object(assemblyai_service, "api_key", "mock_assemblyai_key"):
        with patch("httpx.AsyncClient.post", side_effect=[upload_mock, transcript_mock]):
            with patch("httpx.AsyncClient.get", return_value=poll_mock):
                res = await assemblyai_service.speech_to_text(
                    audio_bytes=b"sample_audio_bytes",
                    language_code="te",
                )
                assert res.success is True
                assert res.transcript == "రైతు బంధు పథకం అర్హతలు ఏమిటి?"
                assert res.language_code == "te"


@pytest.mark.asyncio
async def test_gemini_tts_mock_flow():
    """Verify Gemini TTS audio candidate extraction."""
    mock_part = MagicMock()
    mock_part.inline_data.data = b"RIFF_GEMINI_AUDIO_DATA"
    mock_part.inline_data.mime_type = "audio/wav"

    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]

    mock_genai_response = MagicMock()
    mock_genai_response.candidates = [mock_candidate]

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_genai_response

    mock_client = MagicMock()
    mock_client.models = mock_models

    with patch.object(gemini_tts_service, "api_key", "mock_gemini_key"):
        with patch.object(gemini_tts_service, "_get_client", return_value=mock_client):
            res = await gemini_tts_service.text_to_speech(
                text="నమస్కారం! నేను నితిసేతు సహాయకుడిని.",
                language_code="te-IN",
            )
            assert res.success is True
            assert len(res.audio_base64) > 0
            assert res.language_code == "te-IN"

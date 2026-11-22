from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_law_search_empty_query():
    """Verify that an empty query is rejected by validation."""
    response = client.get("/api/v1/laws/search?q=")
    assert response.status_code == 422


def test_law_search_mock_adapter_fallback():
    """Verify that search succeeds and returns verified statutory provisions from mock adapter."""
    response = client.get("/api/v1/laws/search?q=consumer")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["query"] == "consumer"
    assert data["total_results"] > 0
    assert len(data["results"]) > 0

    first_item = data["results"][0]
    assert "law_name" in first_item
    assert "act_name" in first_item
    assert "section_number" in first_item
    assert "content" in first_item
    assert "source_url" in first_item
    assert "retrieval_timestamp" in first_item


@pytest.mark.asyncio
async def test_law_search_simulated_live_success():
    """Verify that when live NyayKosh API returns 200, is_live_data is True and parsed correctly."""
    mock_live_payload = [
        {
            "title": "The Digital Personal Data Protection Act, 2023",
            "act_name": "DPDP Act 2023",
            "slug": "dpdp-act-2023",
            "category": "Data Protection",
            "provisions": [
                {
                    "section_number": "Section 4",
                    "text": "A person may process the personal data of a Data Principal only in accordance with the provisions of this Act.",
                }
            ],
        }
    ]

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_live_payload,
        request=httpx.Request("GET", "https://lawascode.negd.in/laac-api/v1/laws"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        response = client.get("/api/v1/laws/search?q=data")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_live_data"] is True
    assert data["source"] == "nyaykosh"
    assert len(data["results"]) == 1
    assert data["results"][0]["section_number"] == "Section 4"


@pytest.mark.asyncio
async def test_law_search_simulated_timeout():
    """Verify that on timeout, the service gracefully falls back to mock adapter without failing."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Connection timed out")):
        response = client.get("/api/v1/laws/search?q=privacy")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_live_data"] is False
    assert data["source"] == "nyaykosh_mock_adapter"
    assert len(data["results"]) > 0


@pytest.mark.asyncio
async def test_law_search_simulated_upstream_500():
    """Verify that on upstream server error, fallback to mock adapter is transparently engaged."""
    mock_resp = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("GET", "https://lawascode.negd.in/laac-api/v1/laws"),
    )
    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        response = client.get("/api/v1/laws/search?q=cyber")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_live_data"] is False
    assert data["source"] == "nyaykosh_mock_adapter"

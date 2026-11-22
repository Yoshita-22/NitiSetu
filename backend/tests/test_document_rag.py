import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.document_repository import document_repository
from app.schemas.document_schemas import DocumentMetadata, DocumentPage
from app.services.document_service import document_service

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_document():
    """Setup a sample government circular document with known pages for RAG testing."""
    doc_id = "test_rag_circular_doc_001"
    user_id = "citizen_dev_rag"

    pages = [
        DocumentPage(
            page_number=1,
            text=(
                "Government of India\n"
                "Ministry of Consumer Affairs, Food and Public Distribution\n\n"
                "Section 1. Notification on Consumer Mediation Cells.\n\n"
                "In exercise of powers conferred by Section 74 of the Consumer Protection Act, 2019, "
                "the Central Government hereby establishes Consumer Mediation Cells attached to every District Commission.\n\n"
                "The mediation fee shall be fully subsidized for senior citizens aged 65 years or above."
            ),
            word_count=55,
            character_count=370,
        ),
        DocumentPage(
            page_number=2,
            text=(
                "Section 2. Mandatory Timelines and Penalties.\n\n"
                "Every mediation proceeding under these rules shall be completed within a period of thirty days "
                "from the date of first appearance of parties.\n\n"
                "Failure to comply with settlement terms shall attract a statutory penalty of Rs. 10,000 "
                "payable to the Consumer Welfare Fund."
            ),
            word_count=48,
            character_count=320,
        ),
    ]

    meta = DocumentMetadata(
        document_id=doc_id,
        original_filename="consumer_mediation_circular_2026.pdf",
        file_size_bytes=45000,
        file_type="application/pdf",
        page_count=2,
        upload_timestamp="2026-11-22T10:00:00Z",
        processing_status="EXTRACTED",
        owner_id=user_id,
    )

    document_repository.save_document(meta, pages)
    # Index the document
    document_service.index_document(doc_id, owner_id=user_id)

    yield doc_id, user_id

    # Cleanup
    document_service.delete_document(doc_id, owner_id=user_id)


def test_document_index_status_endpoint(setup_test_document):
    """Verify GET /api/v1/documents/{document_id}/status reports INDEXED state and chunk counts."""
    doc_id, user_id = setup_test_document

    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == doc_id
    assert data["processing_status"] == "INDEXED"
    assert data["chunks_count"] > 0
    assert data["embedding_model"] is not None


def test_document_rag_relevant_query(setup_test_document):
    """Verify that asking a question answered by the document returns a grounded answer with page citations."""
    doc_id, user_id = setup_test_document

    payload = {
        "query": "What is the penalty for failing to comply with settlement terms?",
        "user_id": user_id,
    }

    response = client.post(f"/api/v1/documents/{doc_id}/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["retrieval_status"] == "SUCCESS"
    assert data["grounding_status"] in ("GROUNDED", "PARTIALLY_GROUNDED")
    assert len(data["sources"]) > 0

    # Must cite Page 2 where penalties are defined
    page_numbers = [s["page_number"] for s in data["sources"]]
    assert 2 in page_numbers
    # Must mention Rs. 10,000 penalty in answer or excerpt
    assert "10,000" in data["answer"] or "penalty" in data["answer"].lower()


def test_document_rag_subsidized_fee_query(setup_test_document):
    """Verify that querying mediation fee subsidies cites Page 1."""
    doc_id, user_id = setup_test_document

    payload = {
        "query": "Who is eligible for fully subsidized mediation fee?",
        "user_id": user_id,
    }

    response = client.post(f"/api/v1/documents/{doc_id}/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["retrieval_status"] == "SUCCESS"
    page_numbers = [s["page_number"] for s in data["sources"]]
    assert 1 in page_numbers
    assert "senior citizen" in data["answer"].lower() or "65" in data["answer"]


def test_document_rag_irrelevant_query_insufficient_context(setup_test_document):
    """Verify that asking a completely unrelated question returns insufficient context without fabricating."""
    doc_id, user_id = setup_test_document

    payload = {
        "query": "What is the procedure for launching an artificial satellite into orbit?",
        "user_id": user_id,
        "similarity_threshold": 0.85,
    }

    response = client.post(f"/api/v1/documents/{doc_id}/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["retrieval_status"] == "NO_RELEVANT_CONTEXT"
    assert data["grounding_status"] == "INSUFFICIENT_CONTEXT"
    assert "not find sufficient information" in data["answer"].lower()


def test_document_rag_unauthorized_user_blocked(setup_test_document):
    """Verify unauthorized user cannot query another user's private document."""
    doc_id, _ = setup_test_document

    payload = {
        "query": "Tell me the mediation fee",
        "user_id": "malicious_intruder",
    }

    response = client.post(
        f"/api/v1/documents/{doc_id}/query",
        json=payload,
        headers={"x-user-id": "malicious_intruder"},
    )
    assert response.status_code == 403


def test_document_chunks_inspection(setup_test_document):
    """Verify GET /api/v1/documents/{document_id}/chunks returns structured chunks for authorized user."""
    doc_id, user_id = setup_test_document

    response = client.get(
        f"/api/v1/documents/{doc_id}/chunks",
        headers={"x-user-id": user_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_chunks"] > 0
    assert len(data["chunks"]) == data["total_chunks"]
    assert data["chunks"][0]["metadata"]["document_id"] == doc_id

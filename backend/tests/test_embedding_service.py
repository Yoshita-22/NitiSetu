import pytest
from app.services.embedding_service import EmbeddingService


def test_embedding_service_dimensions_and_metadata():
    """Verify embedding service reports valid dimensions and model metadata."""
    service = EmbeddingService()
    info = service.get_model_information()
    assert "model_name" in info
    assert "dimension" in info
    assert info["dimension"] > 0
    assert service.get_embedding_dimension() == info["dimension"]


def test_embedding_service_query_and_docs():
    """Verify document batch and query embeddings produce consistent vector sizes."""
    service = EmbeddingService()
    dim = service.get_embedding_dimension()

    # Query embedding
    q_emb = service.embed_query("What are the scholarship conditions?")
    assert isinstance(q_emb, list)
    assert len(q_emb) == dim

    # Document embeddings batch
    docs = [
        "Government of India notification regarding farmer subsidies.",
        "Section 12 of Consumer Protection Act establishes consumer mediation cells.",
    ]
    doc_embs = service.embed_documents(docs)
    assert len(doc_embs) == 2
    for emb in doc_embs:
        assert isinstance(emb, list)
        assert len(emb) == dim


def test_embedding_service_multilingual_inputs():
    """Verify embeddings work seamlessly across English, Hindi, and Telugu inputs."""
    service = EmbeddingService()
    dim = service.get_embedding_dimension()

    multilingual_texts = [
        "What is the eligibility for PM Kisan?",
        "पीएम किसान सम्मान निधि योजना के तहत पात्रता नियम क्या हैं?",
        "రైతు బంధు పథకం అర్హతలు ఏమిటి?",
    ]
    embeddings = service.embed_documents(multilingual_texts)
    assert len(embeddings) == 3
    for emb in embeddings:
        assert len(emb) == dim
        # Check non-zero vector
        assert sum(abs(x) for x in emb) > 0.0


def test_embedding_service_empty_input():
    """Verify empty input returns empty or zero vector safely without error."""
    service = EmbeddingService()
    dim = service.get_embedding_dimension()

    empty_docs = service.embed_documents([])
    assert empty_docs == []

    empty_q = service.embed_query("")
    assert len(empty_q) == dim

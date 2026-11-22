import pytest
from app.schemas.document_schemas import DocumentPage
from app.services.chunking_service import ChunkingService


def test_chunking_basic_flow():
    """Verify that document pages are split into structured chunks with valid metadata."""
    chunker = ChunkingService(chunk_size_tokens=50, chunk_overlap_tokens=10)

    pages = [
        DocumentPage(
            page_number=1,
            text=(
                "Section 1. Short Title and Commencement.\n\n"
                "This Act may be called the Civic Rights Act, 2026. "
                "It extends to the whole of India and shall come into force at once.\n\n"
                "Section 2. Definitions.\n\n"
                "In this Act, unless the context otherwise requires, citizen means any individual "
                "entitled to statutory welfare benefits under central or state schemes."
            ),
            word_count=52,
            character_count=310,
        ),
        DocumentPage(
            page_number=2,
            text=(
                "Section 3. Eligibility Conditions.\n\n"
                "Every applicant must be a resident of India and possess valid identification. "
                "No person shall be disqualified on the basis of economic status alone.\n\n"
                "Section 4. Penalties.\n\n"
                "Any officer failing to provide statutory records within thirty days shall be liable to fine."
            ),
            word_count=48,
            character_count=290,
        ),
    ]

    chunks = chunker.chunk_document(
        pages=pages,
        document_id="doc_chunk_test_01",
        user_id="citizen_alice",
        source_filename="civic_rights_act.pdf",
    )

    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c.chunk_id == f"doc_chunk_test_01_chunk_{i}"
        assert c.metadata.document_id == "doc_chunk_test_01"
        assert c.metadata.user_id == "citizen_alice"
        assert c.metadata.source_filename == "civic_rights_act.pdf"
        assert c.metadata.page_start in (1, 2)
        assert c.metadata.page_end in (1, 2)
        assert len(c.content.strip()) > 0
        assert c.metadata.token_count > 0


def test_chunking_heading_preservation():
    """Verify that section headings are extracted and retained in metadata."""
    chunker = ChunkingService(chunk_size_tokens=100, chunk_overlap_tokens=20)
    pages = [
        DocumentPage(
            page_number=1,
            text="Section 45A: Mandatory Disclosure Guidelines\n\nAll departments must publish circulars.",
            word_count=10,
            character_count=80,
        )
    ]
    chunks = chunker.chunk_document(pages, "doc_h", "user_1")
    assert len(chunks) == 1
    assert chunks[0].metadata.section_heading is not None
    assert "Section 45A" in chunks[0].metadata.section_heading


def test_chunking_empty_pages():
    """Verify that empty or blank document pages result in zero chunks without crashing."""
    chunker = ChunkingService()
    pages = [
        DocumentPage(page_number=1, text="", word_count=0, character_count=0),
        DocumentPage(page_number=2, text="   \n\n   ", word_count=0, character_count=0),
    ]
    chunks = chunker.chunk_document(pages, "doc_empty", "user_2")
    assert len(chunks) == 0


def test_chunking_multi_page_span():
    """Verify that chunks preserve page_start and page_end appropriately across page transitions."""
    chunker = ChunkingService(chunk_size_tokens=80, chunk_overlap_tokens=20)
    pages = [
        DocumentPage(page_number=1, text="Paragraph on page one introducing the topic.", word_count=7, character_count=45),
        DocumentPage(page_number=2, text="Paragraph continuing on page two with further details.", word_count=8, character_count=54),
    ]
    chunks = chunker.chunk_document(pages, "doc_span", "user_3")
    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.metadata.page_start == 1

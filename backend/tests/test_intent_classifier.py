import pytest
from app.schemas.intent_schema import IntentType
from app.services.intent_classifier_service import (
    DeterministicFallbackClassifier,
    intent_classifier_service,
)


@pytest.mark.asyncio
async def test_deterministic_fallback_law_query():
    """Verify deterministic fallback correctly classifies law and legal questions."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("What is Section 498A of IPC?")
    assert res.intent == IntentType.LAW_INFORMATION
    assert res.extracted_entities.section_number == "498A"
    assert res.source == "fallback"


@pytest.mark.asyncio
async def test_deterministic_fallback_scheme_query():
    """Verify deterministic fallback identifies schemes like PM-KISAN."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("Tell me about PM-KISAN scheme benefits")
    assert res.intent in (IntentType.SCHEME_INFORMATION, IntentType.SCHEME_ELIGIBILITY)
    assert res.extracted_entities.scheme_id == "PM_KISAN"


@pytest.mark.asyncio
async def test_deterministic_fallback_eligibility_query():
    """Verify eligibility queries are correctly classified."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("Am I eligible for Rythu Bharosa scheme in Telangana?")
    assert res.intent == IntentType.SCHEME_ELIGIBILITY
    assert res.extracted_entities.scheme_id == "TELANGANA_RYTHU_BANDHU"


@pytest.mark.asyncio
async def test_deterministic_fallback_multilingual_hindi():
    """Verify Hindi query language detection and classification."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("पीएम किसान योजना के लिए क्या पात्रता है?")
    assert res.detected_language == "hi"
    assert res.intent == IntentType.SCHEME_ELIGIBILITY


@pytest.mark.asyncio
async def test_deterministic_fallback_multilingual_telugu():
    """Verify Telugu query language detection and classification."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("రైతు బంధు పథకం అర్హతలు ఏమిటి?")
    assert res.detected_language == "te"
    assert res.intent == IntentType.SCHEME_ELIGIBILITY


@pytest.mark.asyncio
async def test_deterministic_fallback_multi_intent():
    """Verify multi-intent classification when asking about law and scheme together."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("Tell me about RTI Act and PM-KISAN scheme")
    assert res.intent == IntentType.MULTI_INTENT
    assert len(res.secondary_intents) >= 2


@pytest.mark.asyncio
async def test_deterministic_fallback_unsupported():
    """Verify out-of-scope non-civic questions are categorized as UNSUPPORTED_QUERY."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("What is the recipe for chicken biryani?")
    assert res.intent == IntentType.UNSUPPORTED_QUERY


@pytest.mark.asyncio
async def test_deterministic_fallback_general_greeting():
    """Verify greetings are classified as GENERAL_QUERY."""
    classifier = DeterministicFallbackClassifier()
    res = classifier.classify("Hello, how can you help me?")
    assert res.intent == IntentType.GENERAL_QUERY


@pytest.mark.asyncio
async def test_service_classify_query_wrapper():
    """Verify public service classify_query handles queries smoothly."""
    res = await intent_classifier_service.classify_query("Tell me about Ayushman Bharat")
    assert res.intent in (IntentType.SCHEME_INFORMATION, IntentType.SCHEME_ELIGIBILITY)
    assert res.detected_language == "en"

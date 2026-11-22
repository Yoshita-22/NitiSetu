import json
import logging
import re
from typing import Optional
from app.core.config import settings
from app.schemas.intent_schema import (
    ExtractedEntities,
    IntentClassification,
    IntentType,
)

logger = logging.getLogger("nitsetu.intent_classifier")

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None


class DeterministicFallbackClassifier:
    """Robust keyword and pattern-based classifier when Groq is unreachable.

    Understands English, Hindi (Devanagari), and Telugu (Telugu script / transliteration)
    civic queries, and transparently sets source="fallback".
    """

    # Keyword rules for intent detection
    LAW_KEYWORDS = [
        "law", "act", "section", "article", "right", "statute", "court",
        "legal", "constitution", "dpdp", "aadhaar act", "consumer protection",
        "धारा", "कानून", "अधिकार", "अधिनियम", "संविधान",
        "చట్టం", "హక్కు", "సెక్షన్", "ఆర్టికల్", "న్యాయం", "రక్షణ"
    ]

    SCHEME_KEYWORDS = [
        "scheme", "yojana", "pm kisan", "pm-kisan", "pmjay", "ayushman", "pmay",
        "rythu bandhu", "rythu bharosa", "scholarship", "subsidy", "kisan samman",
        "योजना", "पीएम किसान", "आयुष्मान", "सब्सिडी", "छात्रवृत्ति",
        "పథకం", "రైతు బంధు", "ఆయుష్మాన్", "స్కాలర్‌షిప్"
    ]

    ELIGIBILITY_TRIGGERS = [
        "eligible", "eligibility", "am i eligible", "can i get", "qualify", "check my",
        "అర్హత", "నాకు వస్తుందా", "అర్హుడనా", "అర్హురాలినా",
        "पात्र", "पात्रता", "क्या मुझे मिलेगा", "योग्यता", "क्या मैं योग्य हूँ"
    ]

    DOCUMENT_KEYWORDS = [
        "document", "pdf", "notice", "circular", "uploaded", "gazette", "file", "order",
        "दस्तावेज़", "पीडीएफ", "नोटिस", "सर्कुलर",
        "పత్రం", "పిడిఎఫ్", "నోటీస్", "సర్క్యులర్"
    ]

    GREETING_KEYWORDS = [
        "hello", "hi", "hey", "namaste", "good morning", "good evening", "how are you",
        "नमस्ते", "प्रणाम", "नमस्कार", "నమస్కారం", "బాగున్నారా"
    ]

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detect language using unicode block ranges."""
        # Devanagari range: \u0900 - \u097F
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        # Telugu range: \u0C00 - \u0C7F
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "te"
        return "en"

    @classmethod
    def classify(cls, query: str, document_id: Optional[str] = None) -> IntentClassification:
        """Classify query deterministically without an LLM."""
        q_lower = query.lower()
        detected_lang = cls.detect_language(query)
        entities = ExtractedEntities(document_id=document_id)

        # 1. Check for Document mentions
        has_doc_kw = any(k in q_lower for k in cls.DOCUMENT_KEYWORDS) or bool(document_id)

        # 2. Check for Law mentions
        has_law_kw = any(k in q_lower for k in cls.LAW_KEYWORDS)

        # 3. Check for Scheme mentions
        has_scheme_kw = any(k in q_lower for k in cls.SCHEME_KEYWORDS)

        # 4. Check for Eligibility request
        is_eligibility_req = any(k in q_lower for k in cls.ELIGIBILITY_TRIGGERS)

        # Extract Scheme Name
        if "pm kisan" in q_lower or "pm-kisan" in q_lower or "पीएम किसान" in query or "పిఎం కిసాన్" in query:
            entities.scheme_name = "PM-KISAN"
            entities.scheme_id = "PM_KISAN"
        elif "ayushman" in q_lower or "pmjay" in q_lower or "आयुष्मान" in query or "ఆయుష్మాన్" in query:
            entities.scheme_name = "Ayushman Bharat PM-JAY"
            entities.scheme_id = "AYUSHMAN_BHARAT"
        elif "pmay" in q_lower or "awaas" in q_lower or "आवास" in query:
            entities.scheme_name = "PMAY-G"
            entities.scheme_id = "PMAY_G"
        elif "rythu bandhu" in q_lower or "rythu bharosa" in q_lower or "రైతు బంధు" in query:
            entities.scheme_name = "Rythu Bandhu"
            entities.scheme_id = "TELANGANA_RYTHU_BANDHU"
            entities.location_or_state = "Telangana"
        elif "scholarship" in q_lower or "nsp" in q_lower or "छात्रवृत्ति" in query or "స్కాలర్‌షిప్" in query:
            entities.scheme_name = "NSP-CSSS"
            entities.scheme_id = "NSP_CSSS"

        # Extract Law / Article / Section
        article_match = re.search(r"(article|section|धारा|ఆర్టికల్|సెక్షన్)\s*(\d+[a-zA-Z]*)", q_lower)
        if article_match:
            entities.section_number = article_match.group(2).upper()
        if "consumer" in q_lower or "उपभोक्ता" in query or "వినియోగదారు" in query:
            entities.law_name = "The Consumer Protection Act, 2019"
            entities.legal_topic = "Consumer Rights"
        elif "dpdp" in q_lower or "privacy" in q_lower or "निजता" in query or "గోప్యత" in query:
            entities.law_name = "The Digital Personal Data Protection Act, 2023"
            entities.legal_topic = "Data Privacy"
        elif "aadhaar" in q_lower or "आधार" in query or "ఆధార్" in query:
            entities.law_name = "The Aadhaar Act, 2016"
            entities.legal_topic = "Aadhaar & Subsidies"

        # Classification decision logic
        # Multi-intent combinations
        if has_doc_kw and has_law_kw:
            return IntentClassification(
                intent=IntentType.MULTI_INTENT,
                secondary_intents=[IntentType.DOCUMENT_QUERY, IntentType.LAW_INFORMATION],
                detected_language=detected_lang,
                confidence_score=0.88,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query simultaneously requests uploaded document analysis and applicable statutory law.",
            )

        if has_scheme_kw and is_eligibility_req and ("tell me" in q_lower or "explain" in q_lower or "what is" in q_lower):
            return IntentClassification(
                intent=IntentType.MULTI_INTENT,
                secondary_intents=[IntentType.SCHEME_INFORMATION, IntentType.SCHEME_ELIGIBILITY],
                detected_language=detected_lang,
                confidence_score=0.90,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query requests both welfare scheme explanation and personal eligibility assessment.",
            )

        # Single intent eligibility check takes precedence when citizen asks for qualification/eligibility
        if has_scheme_kw and is_eligibility_req:
            return IntentClassification(
                intent=IntentType.SCHEME_ELIGIBILITY,
                detected_language=detected_lang,
                confidence_score=0.92,
                extracted_entities=entities,
                source="fallback",
                reasoning="Citizen asking for personal qualification or assessment for a government scheme.",
            )

        if has_scheme_kw and has_law_kw:
            return IntentClassification(
                intent=IntentType.MULTI_INTENT,
                secondary_intents=[IntentType.SCHEME_INFORMATION, IntentType.LAW_INFORMATION],
                detected_language=detected_lang,
                confidence_score=0.88,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query requests information about a government scheme and its legal governing statute.",
            )

        if has_scheme_kw:
            return IntentClassification(
                intent=IntentType.SCHEME_INFORMATION,
                detected_language=detected_lang,
                confidence_score=0.90,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query seeks general information, benefits, or overview of a welfare scheme.",
            )

        if has_law_kw:
            return IntentClassification(
                intent=IntentType.LAW_INFORMATION,
                detected_language=detected_lang,
                confidence_score=0.90,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query references Indian statutory laws, legal sections, or constitutional articles.",
            )

        if has_doc_kw:
            return IntentClassification(
                intent=IntentType.DOCUMENT_QUERY,
                detected_language=detected_lang,
                confidence_score=0.85,
                extracted_entities=entities,
                source="fallback",
                reasoning="Query references an uploaded document, circular, or gazette notice.",
            )

        # Check greetings using word boundaries so 'hi' doesn't match 'chicken'
        is_greeting = any(re.search(r"\b" + re.escape(k) + r"\b", q_lower) for k in cls.GREETING_KEYWORDS)
        if is_greeting:
            return IntentClassification(
                intent=IntentType.GENERAL_QUERY,
                detected_language=detected_lang,
                confidence_score=0.95,
                extracted_entities=entities,
                source="fallback",
                reasoning="Conversational greeting or generic assistant inquiry.",
            )

        # Fallback to general query or unsupported if ambiguous
        if len(query.split()) < 3:
            return IntentClassification(
                intent=IntentType.GENERAL_QUERY,
                detected_language=detected_lang,
                confidence_score=0.60,
                extracted_entities=entities,
                source="fallback",
                reasoning="Short query handled with general civic guidance.",
            )

        return IntentClassification(
            intent=IntentType.UNSUPPORTED_QUERY,
            detected_language=detected_lang,
            confidence_score=0.65,
            extracted_entities=entities,
            source="fallback",
            reasoning="Query does not match supported civic domains (laws, welfare schemes, uploaded circulars).",
        )


class IntentClassifierService:
    """Classifies user queries into structured intents using Groq API or deterministic fallback."""

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT_SECONDS
        self._groq_client = None

    def _get_client(self):
        if self._groq_client is None and self.api_key and AsyncGroq:
            self._groq_client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
        return self._groq_client

    async def classify_query(
        self, query: str, document_id: Optional[str] = None
    ) -> IntentClassification:
        """Classify query with Google Gemini or Groq LLM, with deterministic fallback."""
        trimmed = (query or "").strip()
        if not trimmed:
            return IntentClassification(
                intent=IntentType.GENERAL_QUERY,
                detected_language="en",
                confidence_score=1.0,
                extracted_entities=ExtractedEntities(),
                source="fallback",
                reasoning="Empty input query.",
            )

        system_prompt = (
            "You are the central NitiSetu Intent Classifier and Entity Extractor. "
            "Your task is to analyze user queries regarding Indian civic governance, legal statutes, "
            "welfare schemes, and citizen uploaded documents.\n\n"
            "Supported Intents:\n"
            "- LAW_INFORMATION: Queries about Indian laws, statutes, acts, constitutional articles, citizen rights.\n"
            "- SCHEME_INFORMATION: General questions about government welfare schemes, benefits, ministries.\n"
            "- SCHEME_ELIGIBILITY: Queries asking whether the user is eligible or asking for personal eligibility assessment.\n"
            "- DOCUMENT_QUERY: Queries referring to uploaded government gazettes, circulars, orders, PDFs.\n"
            "- MULTI_INTENT: Queries combining two or more domains (e.g. explain uploaded PDF + find law, or explain scheme + check eligibility).\n"
            "- GENERAL_QUERY: Conversational greetings, help requests, basic conversational pleasantries.\n"
            "- UNSUPPORTED_QUERY: Out of scope queries (e.g. sports, entertainment, coding).\n\n"
            "Languages supported: 'en' (English), 'te' (Telugu), 'hi' (Hindi), 'other'.\n\n"
            "Return strictly valid JSON matching this schema:\n"
            "{\n"
            '  "intent": "LAW_INFORMATION | SCHEME_INFORMATION | SCHEME_ELIGIBILITY | DOCUMENT_QUERY | MULTI_INTENT | GENERAL_QUERY | UNSUPPORTED_QUERY",\n'
            '  "secondary_intents": ["INTENT_TYPE"],\n'
            '  "detected_language": "en | te | hi | other",\n'
            '  "confidence_score": 0.0 to 1.0,\n'
            '  "reasoning": "brief explanation",\n'
            '  "extracted_entities": {\n'
            '    "scheme_name": string or null,\n'
            '    "law_act_name": string or null,\n'
            '    "section_number": string or null,\n'
            '    "article_number": string or null,\n'
            '    "keywords": [string]\n'
            "  }\n"
            "}"
        )

        # 1. Try Gemini Multilingual LLM if configured
        if settings.GEMINI_API_KEY:
            try:
                from app.services.gemini_llm_service import gemini_llm_service
                prompt = f"User query: {trimmed}\n\nClassify intent and extract entities as valid JSON."
                parsed = await gemini_llm_service.generate_json(prompt, system_instruction=system_prompt)
                if parsed and "intent" in parsed and parsed["intent"] in IntentType.__members__:
                    return IntentClassification(
                        intent=IntentType(parsed["intent"]),
                        secondary_intents=[
                            IntentType(i) for i in parsed.get("secondary_intents", []) if i in IntentType.__members__
                        ],
                        detected_language=parsed.get("detected_language", "en"),
                        confidence_score=float(parsed.get("confidence_score", 0.95)),
                        extracted_entities=ExtractedEntities(**parsed.get("extracted_entities", {})),
                        source="gemini",
                        reasoning=parsed.get("reasoning", "Classified via Google Gemini multilingual LLM"),
                    )
            except Exception as e:
                logger.warning(f"Gemini intent classification fallback: {str(e)}")

        # 2. Try Groq LLM if configured
        client = self._get_client()
        if not client:
            logger.info("LLM API key not configured. Using deterministic fallback classifier.")
            return DeterministicFallbackClassifier.classify(trimmed, document_id=document_id)

        user_content = f"Query: {trimmed}"
        if document_id:
            user_content += f"\nActive Uploaded Document ID: {document_id}"

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            raw_json = response.choices[0].message.content
            parsed_data = json.loads(raw_json)

            # Ensure document_id is preserved if provided in request
            if document_id and not parsed_data.get("extracted_entities", {}).get("document_id"):
                if "extracted_entities" not in parsed_data:
                    parsed_data["extracted_entities"] = {}
                parsed_data["extracted_entities"]["document_id"] = document_id

            # Parse and validate with Pydantic
            validated = IntentClassification(
                intent=parsed_data.get("intent", IntentType.GENERAL_QUERY),
                secondary_intents=parsed_data.get("secondary_intents", []),
                detected_language=parsed_data.get("detected_language", "en"),
                confidence_score=float(parsed_data.get("confidence_score", 0.9)),
                extracted_entities=ExtractedEntities(**parsed_data.get("extracted_entities", {})),
                source="groq",
                reasoning=parsed_data.get("reasoning", "Classified via Groq LLM"),
            )
            return validated

        except Exception as e:
            logger.warning(f"Groq intent classification failed ({e.__class__.__name__}: {e}). Engaging fallback.")
            fallback = DeterministicFallbackClassifier.classify(trimmed, document_id=document_id)
            fallback.reasoning = f"Groq unavailable ({str(e)[:60]}); classified via deterministic fallback rules."
            return fallback


# Default singleton instance
intent_classifier_service = IntentClassifierService()

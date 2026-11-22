"""Natural Language Answer Extraction Service for NitiSetu.

Extracts structured applicant answers mapped to scheme questionnaire criteria from
conversational citizen utterances in English, Telugu, and Hindi. Supports:
- Boolean (yes/no, అవును/కాదు, हाँ/नहीं)
- Numeric & Indian currency (250000, ₹2,00,000, 2 lakh, రెండు లక్షలు, दो लाख)
- Uncertainty (I don't know, నాకు తెలియదు, पता नहीं) -> status: UNKNOWN
- Refusal / Declined (I don't want to share, చెప్పదలచుకోలేదు, नहीं बताना चाहता) -> status: PREFER_NOT_TO_ANSWER
- Multi-answer extraction from a single sentence
- Correction detection with audit trail tracking
- LLM extraction via Groq (llama-3.3-70b-versatile) with temperature 0.0
- Deterministic regex and rule-based fallback when offline or ambiguous
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.schemas.eligibility_schemas import (
    AnswerStatus,
    ExtractedAnswer,
    ExtractionResult,
    QuestionnaireItem,
    ValidationStatus,
)

logger = logging.getLogger("nitsetu.answer_extraction")

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None


class DeterministicAnswerExtractor:
    """Rule and pattern-based answer extraction engine for English, Telugu, and Hindi.

    Guarantees reliable extraction even when LLM services are offline or rate-limited.
    """

    # Uncertainty triggers -> status = UNKNOWN
    UNCERTAINTY_PATTERNS = [
        # English
        r"\b(?:i\s+)?don'?t\s+know\b",
        r"\bnot\s+sure\b",
        r"\bno\s+idea\b",
        r"\bnot\s+certain\b",
        r"\bcannot\s+say\b",
        r"\bcan'?t\s+say\b",
        r"\bdon'?t\s+remember\b",
        r"\bunaware\b",
        # Telugu
        r"నాకు\s*తెలియదు",
        r"తెలియదు",
        r"గుర్తులేదు",
        r"చెప్పలేను",
        r"సరిగ్గా\s*తెలియదు",
        r"ఐడియా\s*లేదు",
        # Hindi
        r"पता\s*नहीं",
        r"मुझे\s*नहीं\s*मालूम",
        r"मालूम\s*नहीं",
        r"याद\s*नहीं",
        r"निश्चित\s*नहीं",
        r"कह\s*नहीं\s*सकते",
        r"जानकारी\s*नहीं",
    ]

    # Refusal / Declined triggers -> status = PREFER_NOT_TO_ANSWER
    REFUSAL_PATTERNS = [
        # English
        r"\bdon'?t\s+want\s+to\s+share\b",
        r"\bprefer\s+not\s+to\s+(?:say|answer|share)\b",
        r"\bskip\s+(?:this\s+)?question\b",
        r"\bskip\b",
        r"\bprivate\b",
        r"\bwon'?t\s+tell\b",
        r"\bpass\b",
        # Telugu
        r"చెప్పదలచుకోలేదు",
        r"దాటవేయండి",
        r"చెప్పను",
        r"ఇది\s*చెప్పను",
        r"స్కిప్\s*చేయండి",
        r"వ్యక్తిగతం",
        # Hindi
        r"नहीं\s*बताना\s*चाहता",
        r"नहीं\s*बताना\s*चाहती",
        r"छोड़\s*दो",
        r"साझा\s*नहीं\s*करना",
        r"नहीं\s*बताऊंगा",
        r"नहीं\s*बताऊंगी",
        r"स्किप\s*करें",
        r"निजी\s*है",
    ]

    # Boolean Affirmatives -> True
    AFFIRMATIVE_WORDS = {
        # English
        "yes", "yeah", "yep", "sure", "true", "correct", "right", "indeed", "absolutely",
        "i do", "we do", "we own", "i am", "we are", "have", "owns",
        # Telugu
        "అవును", "అవునండి", "ఉంది", "కలిగి ఉన్నాను", "హా", "నిజమే", "అవును ఉంది", "ఉన్నాయి", "కలదు",
        # Hindi
        "हाँ", "हां", "जी हाँ", "हाँ है", "सही है", "पास है", "करता हूँ", "करते हैं", "हाँजी", "है",
    }

    # Boolean Negatives -> False
    NEGATIVE_WORDS = {
        # English
        "no", "nope", "false", "neither", "none", "never", "not",
        "i don't", "we don't", "no we don't", "not having", "don't own", "does not have",
        # Telugu
        "కాదు", "లేదు", "లేవు", "కాదండి", "లేదు మాకు", "ఏమీ లేదు", "వర్తించదు",
        # Hindi
        "नहीं", "ना", "जी नहीं", "नहीं है", "कोई नहीं", "नहीं करता", "नहीं करते", "मत",
    }

    # Ambiguity Triggers -> status = NEEDS_CLARIFICATION
    AMBIGUITY_PATTERNS = [
        r"\bmaybe\b",
        r"\bprobably\b",
        r"\bperhaps\b",
        r"\bnot\s+sure\s+if\b",
        r"బహుశా",
        r"అనుకుంటా",
        r"షాయద్",
        r"शायद",
        r"हो\s*सकता\s*है",
    ]

    # Correction Triggers
    CORRECTION_PATTERNS = [
        r"\bactually\b",
        r"\bcorrection\b",
        r"\bi\s+mean\b",
        r"\bmy\s+mistake\b",
        r"\bnot\s+.*\s+but\b",
        r"\bchanged\s+to\b",
        r"\binstead\s+of\b",
        r"\brevised\b",
        r"నిజానికి",
        r"తప్పుగా\s*చెప్పాను",
        r"సవరణ",
        r"మార్చండి",
        r"असल\s*में",
        r"वास्तव\s*में",
        r"गलती\s*से",
        r"नहीं\s*बल्कि",
        r"सुधार",
    ]

    # Keyword vocabulary mapping words to numbers (Indian numbering)
    NUMBER_WORDS: Dict[str, float] = {
        "one lakh": 100000.0,
        "two lakh": 200000.0,
        "two lakhs": 200000.0,
        "three lakh": 300000.0,
        "three lakhs": 300000.0,
        "four lakh": 400000.0,
        "four lakhs": 400000.0,
        "five lakh": 500000.0,
        "five lakhs": 500000.0,
        "fifty thousand": 50000.0,
        "one crore": 10000000.0,
        # Telugu
        "ఒక లక్ష": 100000.0,
        "రెండు లక్షలు": 200000.0,
        "మూడు లక్షలు": 300000.0,
        "నాలుగు లక్షలు": 400000.0,
        "ఐదు లక్షలు": 500000.0,
        "లక్షన్నర": 150000.0,
        "యాభై వేలు": 50000.0,
        "ఒక కోటి": 10000000.0,
        # Hindi
        "एक लाख": 100000.0,
        "दो लाख": 200000.0,
        "तीन लाख": 300000.0,
        "चार लाख": 400000.0,
        "पांच लाख": 500000.0,
        "पाँच लाख": 500000.0,
        "डेढ़ लाख": 150000.0,
        "ढाई लाख": 250000.0,
        "पचास हजार": 50000.0,
        "पचास हज़ार": 50000.0,
        "एक करोड़": 10000000.0,
    }

    # Criterion-specific trigger keywords for multi-criteria sentence parsing
    CRITERION_TOPIC_KEYWORDS = {
        "annual_family_income": ["income", "earn", "salary", "lakh", "lacs", "రూపాయలు", "ఆదాయం", "సంపాదన", "आय", "वेतन", "लाख", "₹", "rs"],
        "is_landholding_farmer": ["land", "farm", "farmland", "acres", "acre", "cultivable", "భూమి", "ఎకరాలు", "సాగు", "రైతు", "जमीन", "खेती", "एकड़", "किसान"],
        "is_telangana_resident": ["telangana", "resident", "hyderabad", "తెలంగాణ", "నివాసి", "तेलंगाना", "निवासी"],
        "is_rural_resident": ["rural", "village", "gramin", "గ్రామీణ", "పల్లె", "గ్రామం", "ग्रामीण", "गांव"],
        "is_houseless_or_kutcha": ["kutcha", "houseless", "hut", "mud", "కచ్చా", "ఇల్లు లేదు", "గుడిసె", "कच्चा", "बेघर", "झोपड़ी"],
        "owns_pucca_house": ["pucca", "permanent house", "concrete house", "పక్కా ఇల్లు", "భవంతి", "पक्का मकान", "पक्का घर"],
        "holds_constitutional_post": ["minister", "mp", "mla", "mayor", "constitutional", "మంత్రి", "ఎంపీ", "ఎమ్మెల్యే", "మేయర్", "రాజ్యాంగ", "मंत्री", "सांसद", "विधायक"],
        "is_government_employee": ["government employee", "government job", "govt job", "govt employee", "government", "govt", "psu", "ప్రభుత్వ ఉద్యోగి", "ప్రభుత్వ ఉద్యోగం", "सरकारी कर्मचारी", "सरकारी नौकरी"],
        "is_income_tax_payer": ["income tax", "itr", "tax payer", "ఇన్‌కమ్ ట్యాక్స్", "పన్ను", "आयकर", "टैक्स"],
        "owns_motorized_vehicle": ["vehicle", "car", "tractor", "bike", "wheeler", "మోటారు వాహనం", "కారు", "ట్రాక్టర్", "వాహనం", "గాడి", "ट्रैक्टर", "कार", "मोटर वाहन"],
        "is_senior_citizen_70_plus": ["70 years", "senior citizen", "aged 70", "70 సంవత్సరాలు", "వయస్సు 70", "70 वर्ष", "बुजुर्ग"],
        "in_secc_rural_or_urban_deprived": ["secc", "ration card", "bpl", "deprived", "ఎస్ఈసీసీ", "రేషన్ కార్డు", "పేదరిక", "एसईसीसी", "राशन कार्ड"],
        "class_12_percentile_above_80": ["percentile", "class 12", "intermediate", "80th", "80 పర్సంటైల్", "12వ తరగతి", "80 पर्सेंटाइल", "12वीं"],
        "enrolled_regular_degree": ["regular degree", "college", "university", "btech", "degree", "డిగ్రీ", "కళాశాల", "కాలేజ్", "डिग्री", "कॉलेज"],
        "receives_other_scholarship": ["other scholarship", "stipend", "ఇతర స్కాలర్‌షిప్", "వేరే స్కాలర్‌షిప్", "अन्य छात्रवृत्ति", "वजीफा"],
        "has_dharani_pattadar_passbook": ["dharani", "pattadar", "passbook", "ధరణి", "పట్టాదారు", "పాస్‌పుస్తకం", "धरणी", "पट्टादार", "पासबुक"],
        "is_cultivable_agricultural_land": ["cultivable land", "agricultural land", "సాగు భూమి", "వ్యవసాయ భూమి", "कृषि योग्य", "उपजाऊ"],
    }

    @classmethod
    def parse_numeric_expression(cls, text: str) -> Optional[float]:
        """Convert conversational numbers, words, lakhs, and Indian currency into float."""
        clean = text.lower().strip()

        # 1. Match named expressions e.g. "two lakh", "రెండు లక్షలు", "दो लाख"
        for word, val in cls.NUMBER_WORDS.items():
            if word in clean:
                return val

        # 2. Match decimal/integer with lakh unit: e.g. "1.5 lakh", "2.5 లక్షలు", "3 लाख"
        m_lakh = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:lakhs?|lacs?|lac|l|లక్షలు|లక్ష|లాఖ్|लाख|लाखों)(?:\s|$|[^a-zA-Z0-9])",
            clean,
            re.IGNORECASE,
        )
        if m_lakh:
            try:
                return float(m_lakh.group(1)) * 100000.0
            except ValueError:
                pass

        # 3. Match comma formatted numbers e.g. ₹2,00,000, Rs. 50,000
        m_comma = re.search(
            r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]+)?)",
            clean,
            re.IGNORECASE,
        )
        if m_comma:
            try:
                num_str = m_comma.group(1).replace(",", "")
                return float(num_str)
            except ValueError:
                pass

        # 4. Match plain numeric digits e.g. 250000, 300000
        m_num = re.search(
            r"(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)",
            clean,
            re.IGNORECASE,
        )
        if m_num:
            try:
                return float(m_num.group(1))
            except ValueError:
                pass

        return None

    @classmethod
    def check_correction(cls, text: str) -> bool:
        """Check if message contains explicit correction keywords."""
        for pattern in cls.CORRECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def matches_keyword(cls, keyword: str, text: str) -> bool:
        """Check if keyword matches as a distinct word or token, avoiding substring false positives."""
        pattern = (
            r"(?:^|[^a-zA-Z0-9\u0C00-\u0C7F\u0900-\u097F])"
            + re.escape(keyword.lower())
            + r"(?:$|[^a-zA-Z0-9\u0C00-\u0C7F\u0900-\u097F])"
        )
        return bool(re.search(pattern, text.lower()))

    @classmethod
    def extract(
        cls,
        user_message: str,
        active_questions: List[QuestionnaireItem],
        existing_answers: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        """Extract structured criteria answers deterministically."""
        existing_answers = existing_answers or {}
        context = context or {}
        trimmed = user_message.strip()
        msg_lower = trimmed.lower()

        if not trimmed:
            return ExtractionResult(
                answers=[],
                raw_message=user_message,
                source="deterministic_fallback",
            )

        extracted: List[ExtractedAnswer] = []
        is_correction = cls.check_correction(trimmed)
        current_qid = context.get("current_question_id")

        # 1. Check for Uncertainty across entire message
        is_uncertain = any(re.search(p, msg_lower) for p in cls.UNCERTAINTY_PATTERNS)

        # 2. Check for Refusal / Declined across entire message
        is_refusal = any(re.search(p, msg_lower) for p in cls.REFUSAL_PATTERNS)

        # 3. Check for Ambiguity
        is_ambiguous = any(re.search(p, msg_lower) for p in cls.AMBIGUITY_PATTERNS)

        # Build lookup for active criteria
        active_map = {q.id: q for q in active_questions}

        # Case A: Uncertainty stated for current focused question
        if is_uncertain and current_qid and current_qid in active_map and not is_correction:
            # Only trigger if user didn't mention other criteria
            has_other_kws = any(
                any(cls.matches_keyword(k, msg_lower) for k in cls.CRITERION_TOPIC_KEYWORDS.get(q.id, []))
                for q in active_questions
                if q.id != current_qid
            )
            if not has_other_kws:
                q = active_map[current_qid]
                extracted.append(
                    ExtractedAnswer(
                        criterion_id=q.id,
                        extracted_value=None,
                        status="UNKNOWN",
                        validation_status="VALID",
                        raw_text=trimmed,
                        confidence=0.95,
                        is_correction=False,
                        source="deterministic_fallback",
                        reasoning="Citizen indicated they do not know or are unsure.",
                    )
                )
                return ExtractionResult(answers=extracted, raw_message=user_message, source="deterministic_fallback")

        # Case B: Refusal stated for current focused question
        if is_refusal and current_qid and current_qid in active_map:
            q = active_map[current_qid]
            extracted.append(
                ExtractedAnswer(
                    criterion_id=q.id,
                    extracted_value=None,
                    status="PREFER_NOT_TO_ANSWER",
                    validation_status="VALID",
                    raw_text=trimmed,
                    confidence=0.95,
                    is_correction=False,
                    source="deterministic_fallback",
                    reasoning="Citizen chose to decline or skip this question.",
                )
            )
            return ExtractionResult(answers=extracted, raw_message=user_message, source="deterministic_fallback")

        # Case C: Ambiguous statement
        if is_ambiguous and current_qid and current_qid in active_map:
            q = active_map[current_qid]
            extracted.append(
                ExtractedAnswer(
                    criterion_id=q.id,
                    extracted_value=None,
                    status="NEEDS_CLARIFICATION",
                    validation_status="AMBIGUOUS",
                    raw_text=trimmed,
                    confidence=0.60,
                    is_correction=False,
                    source="deterministic_fallback",
                    clarification_prompt=f"Could you please confirm with a direct Yes or No whether: {q.label}?",
                    reasoning="Citizen gave an ambiguous or tentative response.",
                )
            )
            return ExtractionResult(
                answers=extracted,
                has_clarification_needed=True,
                raw_message=user_message,
                source="deterministic_fallback",
            )

        # Case D: Check topic keywords across active criteria (Multi-criteria or targeted sentence)
        topic_matches = {
            q.id: [k for k in cls.CRITERION_TOPIC_KEYWORDS.get(q.id, []) if cls.matches_keyword(k, msg_lower)]
            for q in active_questions
            if any(cls.matches_keyword(k, msg_lower) for k in cls.CRITERION_TOPIC_KEYWORDS.get(q.id, []))
        }

        if topic_matches:
            clauses = [
                c.strip()
                for c in re.split(r"[,;.\n]|\band\b|\bమరియు\b|\bऔर\b", msg_lower)
                if c.strip()
            ]

            for cid in topic_matches:
                q = active_map[cid]
                prev = existing_answers.get(cid)

                if q.type == "boolean":
                    if len(topic_matches) == 1:
                        eval_clause = msg_lower
                    else:
                        matching_clauses = [
                            cl for cl in clauses if any(cls.matches_keyword(k, cl) for k in topic_matches[cid])
                        ]
                        eval_clause = " ".join(matching_clauses) if matching_clauses else msg_lower

                    neg_words_en = [
                        "no", "not", "none", "neither", "no one", "don't", "dont",
                        "doesn't", "doesnt", "didn't", "did not", "never", "without",
                    ]
                    neg_words_indic = [
                        "లేదు", "కాదు", "లేవు", "కాదండి", "ఏమీ లేదు",
                        "नहीं", "ना", "बिना", "नहीं है"
                    ]
                    has_neg = any(
                        re.search(r"\b" + re.escape(nw) + r"\b", eval_clause) for nw in neg_words_en
                    ) or any(nw in eval_clause for nw in neg_words_indic)
                    val = False if has_neg else True

                    extracted.append(
                        ExtractedAnswer(
                            criterion_id=cid,
                            extracted_value=val,
                            status="ANSWERED",
                            validation_status="VALID",
                            raw_text=trimmed,
                            confidence=0.90,
                            is_correction=is_correction or (prev is not None and prev != val),
                            previous_value=prev,
                            source="deterministic_fallback",
                            reasoning=f"Matched topic keywords in clause '{eval_clause}'.",
                        )
                    )

                elif q.type == "number":
                    num_val = cls.parse_numeric_expression(trimmed)
                    if num_val is not None:
                        extracted.append(
                            ExtractedAnswer(
                                criterion_id=cid,
                                extracted_value=num_val,
                                status="ANSWERED",
                                validation_status="VALID",
                                raw_text=trimmed,
                                confidence=0.95,
                                is_correction=is_correction or (prev is not None and prev != num_val),
                                previous_value=prev,
                                source="deterministic_fallback",
                                reasoning=f"Parsed numeric value for topic {cid}.",
                            )
                        )

            if extracted:
                return ExtractionResult(
                    answers=extracted,
                    raw_message=user_message,
                    source="deterministic_fallback",
                )

        # Case E: Single focused question active and short answer given (when no topic keywords matched)
        if current_qid and current_qid in active_map:
            focus_q = active_map[current_qid]

            # If boolean question:
            if focus_q.type == "boolean":
                # Check affirmative
                is_aff = any(re.search(r"\b" + re.escape(w) + r"\b", msg_lower) for w in cls.AFFIRMATIVE_WORDS) or any(
                    w in trimmed for w in ["అవును", "హా", "हाँ", "ఉంది", "ఉన్నాయి"]
                )
                is_neg = any(re.search(r"\b" + re.escape(w) + r"\b", msg_lower) for w in cls.NEGATIVE_WORDS) or any(
                    w in trimmed for w in ["కాదు", "లేదు", "नहीं", "ना"]
                )

                if is_aff and not is_neg:
                    prev = existing_answers.get(focus_q.id)
                    extracted.append(
                        ExtractedAnswer(
                            criterion_id=focus_q.id,
                            extracted_value=True,
                            status="ANSWERED",
                            validation_status="VALID",
                            raw_text=trimmed,
                            confidence=0.95,
                            is_correction=is_correction or (prev is not None and prev is not True),
                            previous_value=prev,
                            source="deterministic_fallback",
                            reasoning="Direct affirmative confirmation.",
                        )
                    )
                    return ExtractionResult(answers=extracted, raw_message=user_message, source="deterministic_fallback")

                if is_neg and not is_aff:
                    prev = existing_answers.get(focus_q.id)
                    extracted.append(
                        ExtractedAnswer(
                            criterion_id=focus_q.id,
                            extracted_value=False,
                            status="ANSWERED",
                            validation_status="VALID",
                            raw_text=trimmed,
                            confidence=0.95,
                            is_correction=is_correction or (prev is not None and prev is not False),
                            previous_value=prev,
                            source="deterministic_fallback",
                            reasoning="Direct negative confirmation.",
                        )
                    )
                    return ExtractionResult(answers=extracted, raw_message=user_message, source="deterministic_fallback")

            # If numeric question:
            if focus_q.type == "number":
                num_val = cls.parse_numeric_expression(trimmed)
                if num_val is not None:
                    prev = existing_answers.get(focus_q.id)
                    extracted.append(
                        ExtractedAnswer(
                            criterion_id=focus_q.id,
                            extracted_value=num_val,
                            status="ANSWERED",
                            validation_status="VALID",
                            raw_text=trimmed,
                            confidence=0.95,
                            is_correction=is_correction or (prev is not None and prev != num_val),
                            previous_value=prev,
                            source="deterministic_fallback",
                            reasoning="Parsed numeric value from citizen utterance.",
                        )
                    )
                    return ExtractionResult(answers=extracted, raw_message=user_message, source="deterministic_fallback")

        # De-duplicate extracted answers by criterion_id keeping highest confidence
        unique_answers: Dict[str, ExtractedAnswer] = {}
        for ans in extracted:
            if ans.criterion_id not in unique_answers or ans.confidence > unique_answers[ans.criterion_id].confidence:
                unique_answers[ans.criterion_id] = ans

        return ExtractionResult(
            answers=list(unique_answers.values()),
            raw_message=user_message,
            source="deterministic_fallback",
        )


class AnswerExtractionService:
    """Intelligent natural language answer extractor for civic welfare questionnaires.

    Combines Groq LLM extraction (llama-3.3-70b-versatile, temperature 0.0) with
    resilient multilingual deterministic fallback.
    """

    SYSTEM_PROMPT = (
        "You are NitiSetu, an AI civic information assistant in India.\n"
        "Your task is to extract structured questionnaire answers from citizen messages.\n\n"
        "CRITICAL RULES:\n"
        "1. Extract answers ONLY for the provided ACTIVE CRITERIA. Do NOT invent criteria or properties.\n"
        "2. If an applicant says 'I don't know', 'not sure', 'నాకు తెలియదు', or 'पता नहीं', set status to 'UNKNOWN' and extracted_value to null.\n"
        "3. If an applicant declines, refuses, or asks to skip, set status to 'PREFER_NOT_TO_ANSWER' and extracted_value to null.\n"
        "4. NEVER treat UNKNOWN as False. NEVER treat refusal as No.\n"
        "5. For numeric values (like income in lakhs, rupees, or words like 'రెండు లక్షలు', 'दो लाख'), convert to plain numbers (e.g. 200000).\n"
        "6. If the citizen is updating or correcting a previously stated answer (e.g. 'actually 1.5 lakh not 2 lakh'), set is_correction to true and record previous_value.\n"
        "7. If an answer is contradictory, vague, or ambiguous (e.g. 'maybe', 'sometimes'), set status to 'NEEDS_CLARIFICATION' and provide a clarification_prompt.\n"
        "8. Return JSON strictly conforming to the requested schema.\n"
    )

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.timeout = settings.GROQ_TIMEOUT_SECONDS
        self._groq_client = None

    def _get_client(self):
        if self._groq_client is None and self.api_key and AsyncGroq:
            self._groq_client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
        return self._groq_client

    async def extract_answers(
        self,
        user_message: str,
        active_questions: List[QuestionnaireItem],
        existing_answers: Optional[Dict[str, Any]] = None,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        """Extract structured answers from citizen utterance using Groq or fallback.

        Args:
            user_message: Raw message or speech transcript from citizen.
            active_questions: The relevant scheme QuestionnaireItem instances.
            existing_answers: Map of criterion_id to previous value or ApplicantAnswer.
            language: Interaction language code ('en', 'te', 'hi').
            context: Additional assessment context (e.g. 'scheme_id', 'current_question_id').

        Returns:
            ExtractionResult: Container with extracted answers and source provenance.
        """
        existing_answers = existing_answers or {}
        context = context or {}
        trimmed = (user_message or "").strip()

        if not trimmed or not active_questions:
            return ExtractionResult(
                answers=[],
                raw_message=user_message,
                source="deterministic_fallback",
            )

        # Extract plain values from existing_answers if they are ApplicantAnswer instances
        clean_existing: Dict[str, Any] = {}
        for k, v in existing_answers.items():
            if hasattr(v, "value"):
                clean_existing[k] = v.value
            else:
                clean_existing[k] = v

        client = self._get_client()
        if not client:
            logger.info("Groq client unavailable. Using deterministic answer extractor.")
            return DeterministicAnswerExtractor.extract(
                trimmed, active_questions, clean_existing, context
            )

        # Prepare payload for Groq
        active_schema = [
            {
                "criterion_id": q.id,
                "label": q.label,
                "type": q.type,
                "category": q.category,
                "help_text": q.help_text,
                "required": q.required,
            }
            for q in active_questions
        ]

        user_prompt = (
            f"Citizen Message: \"{trimmed}\"\n"
            f"Conversation Language: {language}\n"
            f"Current Focused Question ID: {context.get('current_question_id')}\n"
            f"Existing Answers: {json.dumps(clean_existing)}\n"
            f"Active Criteria List:\n{json.dumps(active_schema, indent=2)}\n\n"
            "Extract any matching criteria answers. Return JSON matching schema:\n"
            "{\n"
            '  "answers": [\n'
            '    {\n'
            '      "criterion_id": "string",\n'
            '      "extracted_value": true/false/number/string/null,\n'
            '      "status": "ANSWERED" | "UNKNOWN" | "NOT_APPLICABLE" | "PREFER_NOT_TO_ANSWER" | "NEEDS_CLARIFICATION",\n'
            '      "validation_status": "VALID" | "INVALID" | "AMBIGUOUS" | "CORRECTION",\n'
            '      "raw_text": "string",\n'
            '      "confidence": 0.0 to 1.0,\n'
            '      "is_correction": boolean,\n'
            '      "previous_value": any or null,\n'
            '      "clarification_prompt": "string or null",\n'
            '      "reasoning": "brief explanation"\n'
            '    }\n'
            '  ],\n'
            '  "unmatched_text": "string or null",\n'
            '  "has_clarification_needed": boolean\n'
            "}"
        )

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )

            raw_json = response.choices[0].message.content
            data = json.loads(raw_json)

            extracted_items: List[ExtractedAnswer] = []
            active_ids = {q.id for q in active_questions}

            for item in data.get("answers", []):
                cid = item.get("criterion_id")
                # Strictly drop hallucinated criteria not in active criteria
                if cid not in active_ids:
                    continue

                extracted_items.append(
                    ExtractedAnswer(
                        criterion_id=cid,
                        extracted_value=item.get("extracted_value"),
                        status=item.get("status", "ANSWERED"),
                        validation_status=item.get("validation_status", "VALID"),
                        raw_text=item.get("raw_text") or trimmed,
                        confidence=float(item.get("confidence", 0.95)),
                        is_correction=bool(item.get("is_correction", False)),
                        previous_value=item.get("previous_value") or clean_existing.get(cid),
                        source="llm",
                        clarification_prompt=item.get("clarification_prompt"),
                        reasoning=item.get("reasoning"),
                    )
                )

            return ExtractionResult(
                answers=extracted_items,
                unmatched_text=data.get("unmatched_text"),
                has_clarification_needed=any(a.status == "NEEDS_CLARIFICATION" for a in extracted_items),
                source="llm",
                raw_message=user_message,
            )

        except Exception as e:
            logger.warning(
                f"Groq answer extraction failed ({type(e).__name__}: {str(e)}). Falling back to deterministic extractor."
            )
            return DeterministicAnswerExtractor.extract(
                trimmed, active_questions, clean_existing, context
            )

    def extract_answers_sync(
        self,
        user_message: str,
        active_questions: List[QuestionnaireItem],
        existing_answers: Optional[Dict[str, Any]] = None,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        """Synchronous wrapper for deterministic answer extraction."""
        return DeterministicAnswerExtractor.extract(
            user_message, active_questions, existing_answers, context
        )


# Default service instance
answer_extraction_service = AnswerExtractionService()

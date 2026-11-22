"""Answer Validation Service for NitiSetu.

Validates extracted citizen answers against criterion-specific rules, input types,
and boundary conditions. Performs early statutory disqualification checks, handles
uncertainty/refusal gracefully, and generates citizen-friendly multilingual error
and clarification messages in English, Telugu, and Hindi.
"""

import logging
from typing import Any, Dict, List, Optional
from app.schemas.eligibility_schemas import (
    AnswerStatus,
    CriterionValidationRule,
    ExtractedAnswer,
    ExtractionResult,
    QuestionnaireItem,
    ValidatedAnswer,
    ValidationReport,
    ValidationStatus,
)
from app.services.questionnaire_mapping_service import questionnaire_mapping_service

logger = logging.getLogger("nitsetu.answer_validation")


class AnswerValidationService:
    """Service evaluating validity, type-conformance, and statutory impact of applicant answers."""

    # Statutory disqualification rules for known criteria across the 5 schemes
    DISQUALIFICATION_RULES: Dict[str, Dict[str, Any]] = {
        "is_landholding_farmer": {
            "disqualifying_value": False,
            "statutory_note": "Landless farmers or families without recorded land ownership are statutorily ineligible under PM-KISAN.",
        },
        "holds_constitutional_post": {
            "disqualifying_value": True,
            "statutory_note": "Holders of constitutional posts (Ministers, MPs, MLAs, Mayors) are statutorily disqualified from PM-KISAN.",
        },
        "is_government_employee": {
            "disqualifying_value": True,
            "statutory_note": "Regular government and PSU employees (excluding Class IV / MTS) are statutorily excluded.",
        },
        "is_income_tax_payer": {
            "disqualifying_value": True,
            "statutory_note": "Income tax payers in the last assessment year are statutorily excluded.",
        },
        "monthly_pension_over_10k": {
            "disqualifying_value": True,
            "statutory_note": "Pensioners receiving monthly pension of Rs. 10,000 or more are excluded.",
        },
        "owns_motorized_vehicle": {
            "disqualifying_value": True,
            "statutory_note": "Motor vehicle or mechanized farm equipment ownership constitutes a statutory exclusion under standard PM-JAY and PMAY-G.",
        },
        "is_rural_resident": {
            "disqualifying_value": False,
            "statutory_note": "PMAY-G is strictly restricted to rural territories (Gramin). Urban residents must apply under PMAY-U.",
        },
        "owns_pucca_house": {
            "disqualifying_value": True,
            "statutory_note": "Families owning a permanent pucca house anywhere in India are strictly disqualified from PMAY-G.",
        },
        "monthly_income_over_15k": {
            "disqualifying_value": True,
            "statutory_note": "Household monthly earnings exceeding Rs. 15,000 exceed the rural deprivation ceiling for PMAY-G.",
        },
        "class_12_percentile_above_80": {
            "disqualifying_value": False,
            "statutory_note": "Scoring below the 80th percentile merit cutoff in Class 12 board examination disqualifies NSP-CSSS applicants.",
        },
        "enrolled_regular_degree": {
            "disqualifying_value": False,
            "statutory_note": "Distance, correspondence, or diploma courses are excluded from the Central Sector Scholarship Scheme.",
        },
        "annual_family_income": {
            "threshold_max": 450000.0,
            "statutory_note": "Parental gross annual income exceeds the statutory Rs. 4,50,000 per annum ceiling for NSP-CSSS.",
        },
        "receives_other_scholarship": {
            "disqualifying_value": True,
            "statutory_note": "Concurrent receipt of other Central or State government scholarships is prohibited to prevent double dipping.",
        },
        "is_telangana_resident": {
            "disqualifying_value": False,
            "statutory_note": "Rythu Bandhu / Rythu Bharosa is restricted to resident cultivators within Telangana State.",
        },
        "has_dharani_pattadar_passbook": {
            "disqualifying_value": False,
            "statutory_note": "Possession of an active digital Pattadar Passbook in the Dharani portal is mandatory.",
        },
        "is_cultivable_agricultural_land": {
            "disqualifying_value": False,
            "statutory_note": "Commercial, real estate layouts, and barren non-cultivable plots are excluded from agricultural investment assistance.",
        },
    }

    # Multilingual validation error templates
    LOCALIZED_MESSAGES = {
        "en": {
            "boolean_error": "Please answer Yes or No for '{label}'.",
            "number_error": "Please enter a valid numeric value for '{label}'.",
            "min_error": "Value must be at least {min} for '{label}'.",
            "max_error": "Value cannot exceed {max} for '{label}'.",
            "select_error": "Please choose from one of the allowed options: {options}.",
            "ambiguous_clarification": "Could you please clarify whether: {label}?",
        },
        "te": {
            "boolean_error": "'{label}' కొరకు దయచేసి అవును లేదా కాదు అని సమాధానం ఇవ్వండి.",
            "number_error": "'{label}' కొరకు దయచేసి సరైన సంఖ్యను నమోదు చేయండి.",
            "min_error": "'{label}' విలువ కనీసం {min} ఉండాలి.",
            "max_error": "'{label}' విలువ {max} కంటే ఎక్కువ ఉండకూడదు.",
            "select_error": "దయచేసి అనుమతించబడిన ఎంపికలలో ఒకదాన్ని ఎంచుకోండి: {options}.",
            "ambiguous_clarification": "దయచేసి స్పష్టత ఇవ్వండి: {label}?",
        },
        "hi": {
            "boolean_error": "'{label}' के लिए कृपया हाँ या नहीं में उत्तर दें।",
            "number_error": "'{label}' के लिए कृपया एक मान्य संख्यात्मक मान दर्ज करें।",
            "min_error": "'{label}' का मान कम से कम {min} होना चाहिए।",
            "max_error": "'{label}' का मान {max} से अधिक नहीं हो सकता।",
            "select_error": "कृपया अनुमत विकल्पों में से एक का चयन करें: {options}।",
            "ambiguous_clarification": "कृपया स्पष्ट करें: {label}?",
        },
    }

    def _get_localized_templates(self, language: str) -> Dict[str, str]:
        """Retrieve message templates for specified language code with English fallback."""
        lang = language.lower() if language else "en"
        return self.LOCALIZED_MESSAGES.get(lang, self.LOCALIZED_MESSAGES["en"])

    def validate_answer(
        self,
        extracted: ExtractedAnswer,
        question: QuestionnaireItem,
        scheme_id: Optional[str] = None,
        language: str = "en",
    ) -> ValidatedAnswer:
        """Validate an ExtractedAnswer against its QuestionnaireItem definition and validation rules.

        Args:
            extracted: The candidate ExtractedAnswer produced by answer extraction.
            question: The underlying QuestionnaireItem containing criterion rules.
            scheme_id: Optional scheme identifier to contextualize statutory checks.
            language: Interaction language code ('en', 'te', 'hi').

        Returns:
            ValidatedAnswer: Structured validation report for this criterion.
        """
        templates = self._get_localized_templates(language)
        label = question.label
        cid = question.id
        status = extracted.status
        val = extracted.extracted_value

        # 1. Non-terminal / Null value statuses: UNKNOWN, PREFER_NOT_TO_ANSWER, NOT_APPLICABLE
        if status in ("UNKNOWN", "PREFER_NOT_TO_ANSWER", "NOT_APPLICABLE"):
            return ValidatedAnswer(
                criterion_id=cid,
                is_valid=True,
                validation_status="VALID",
                normalized_value=None,
                error_message=None,
                clarification_prompt=None,
                requires_clarification=False,
                is_disqualifying=False,
                statutory_note=None,
            )

        # 2. Needs Clarification / Ambiguous
        if status == "NEEDS_CLARIFICATION" or extracted.validation_status == "AMBIGUOUS":
            prompt = extracted.clarification_prompt or templates["ambiguous_clarification"].format(label=label)
            return ValidatedAnswer(
                criterion_id=cid,
                is_valid=False,
                validation_status="AMBIGUOUS",
                normalized_value=None,
                error_message=None,
                clarification_prompt=prompt,
                requires_clarification=True,
                is_disqualifying=False,
                statutory_note=None,
            )

        # 3. Answered Status -> Validate type and bounds
        normalized_val: Optional[Any] = None
        error_msg: Optional[str] = None

        if question.type == "boolean":
            if isinstance(val, bool):
                normalized_val = val
            elif isinstance(val, str):
                v_lower = val.strip().lower()
                if v_lower in ("yes", "true", "1", "y", "ha", "avunu"):
                    normalized_val = True
                elif v_lower in ("no", "false", "0", "n", "nahi", "kadu"):
                    normalized_val = False
                else:
                    error_msg = templates["boolean_error"].format(label=label)
            else:
                error_msg = templates["boolean_error"].format(label=label)

        elif question.type == "number":
            if val is not None:
                try:
                    num = float(val)
                    rule = question.validation_rule
                    if rule:
                        if rule.min_value is not None and num < rule.min_value:
                            error_msg = templates["min_error"].format(min=rule.min_value, label=label)
                        elif rule.max_value is not None and num > rule.max_value:
                            error_msg = templates["max_error"].format(max=rule.max_value, label=label)
                    if error_msg is None:
                        # Normalize to int if integer value, else float
                        normalized_val = int(num) if num.is_integer() else num
                except (ValueError, TypeError):
                    error_msg = templates["number_error"].format(label=label)
            else:
                error_msg = templates["number_error"].format(label=label)

        elif question.type == "select":
            rule = question.validation_rule
            if rule and rule.allowed_values is not None:
                if val not in rule.allowed_values:
                    allowed_str = ", ".join(str(x) for x in rule.allowed_values)
                    error_msg = templates["select_error"].format(options=allowed_str, label=label)
                else:
                    normalized_val = val
            else:
                normalized_val = val

        elif question.type in ("text", "date"):
            if val is not None:
                normalized_val = str(val).strip()
            else:
                error_msg = f"Value for '{label}' cannot be empty."

        # If data validation failed:
        if error_msg is not None:
            return ValidatedAnswer(
                criterion_id=cid,
                is_valid=False,
                validation_status="INVALID",
                normalized_value=None,
                error_message=error_msg,
                requires_clarification=False,
                is_disqualifying=False,
            )

        # 4. Check for potential statutory disqualification
        is_disq = False
        stat_note: Optional[str] = None
        disq_info = self.DISQUALIFICATION_RULES.get(cid)

        if disq_info and normalized_val is not None:
            # For boolean and equality checks:
            if "disqualifying_value" in disq_info and normalized_val == disq_info["disqualifying_value"]:
                # Exception: Ayushman Bharat senior citizens (70+) bypass vehicle & employee exclusions
                if scheme_id == "AYUSHMAN_BHARAT" and cid in ("owns_motorized_vehicle", "is_government_employee"):
                    # Note: We mark as potentially disqualifying under standard SECC rules
                    is_disq = True
                    stat_note = disq_info["statutory_note"] + " (Senior Citizens aged 70+ may still qualify under Vay Vandana)."
                else:
                    is_disq = True
                    stat_note = disq_info["statutory_note"]

            # For numeric threshold checks (e.g. income limit):
            elif "threshold_max" in disq_info and float(normalized_val) > disq_info["threshold_max"]:
                is_disq = True
                stat_note = disq_info["statutory_note"]

        return ValidatedAnswer(
            criterion_id=cid,
            is_valid=True,
            validation_status="VALID",
            normalized_value=normalized_val,
            error_message=None,
            clarification_prompt=None,
            requires_clarification=False,
            is_disqualifying=is_disq,
            statutory_note=stat_note,
        )

    def validate_extraction_result(
        self,
        result: ExtractionResult,
        active_questions: List[QuestionnaireItem],
        scheme_id: Optional[str] = None,
        language: str = "en",
    ) -> ValidationReport:
        """Validate all answers in an ExtractionResult container against active criteria."""
        q_map = {q.id: q for q in active_questions}
        validated_items: List[ValidatedAnswer] = []
        errors: List[str] = []
        disqualifications: List[str] = []
        has_clarification = False

        for ans in result.answers:
            q = q_map.get(ans.criterion_id)
            if not q:
                continue

            v_ans = self.validate_answer(ans, q, scheme_id=scheme_id, language=language)
            validated_items.append(v_ans)

            if not v_ans.is_valid and v_ans.error_message:
                errors.append(v_ans.error_message)

            if v_ans.requires_clarification:
                has_clarification = True

            if v_ans.is_disqualifying and v_ans.statutory_note:
                disqualifications.append(v_ans.statutory_note)

        all_valid = len(errors) == 0 and not has_clarification

        return ValidationReport(
            is_all_valid=all_valid,
            validated_answers=validated_items,
            errors=errors,
            has_disqualifying_condition=len(disqualifications) > 0,
            disqualifying_reasons=disqualifications,
            requires_clarification=has_clarification,
        )

    def validate_raw_answer(
        self,
        criterion_id: str,
        value: Any,
        scheme_id: str,
        status: AnswerStatus = "ANSWERED",
        language: str = "en",
    ) -> ValidatedAnswer:
        """Convenience method to validate a single raw criterion value directly."""
        q = questionnaire_mapping_service.get_question_by_id(scheme_id, criterion_id, language=language)
        if not q:
            return ValidatedAnswer(
                criterion_id=criterion_id,
                is_valid=False,
                validation_status="INVALID",
                error_message=f"Criterion '{criterion_id}' is not recognized for scheme '{scheme_id}'.",
            )

        extracted = ExtractedAnswer(
            criterion_id=criterion_id,
            extracted_value=value,
            status=status,
            validation_status="VALID",
        )
        return self.validate_answer(extracted, q, scheme_id=scheme_id, language=language)


# Default service instance
answer_validation_service = AnswerValidationService()

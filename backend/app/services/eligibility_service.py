from typing import Any, Dict, List, Optional
from app.core.exceptions import NotFoundError
from app.repositories.scheme_repository import scheme_repository
from app.services.questionnaire_mapping_service import questionnaire_mapping_service
from app.schemas.scheme_schemas import (
    EligibilityConditionResult,
    EligibilityEvaluationResponse,
    EligibilityQuestion,
    EligibilityQuestionsResponse,
)


class EligibilityEvaluationService:
    """Deterministic rule evaluator for government welfare schemes.

    Evaluates citizen input strictly against verified official criteria without
    hallucinating or providing definitive government certifications.
    """

    SCHEME_QUESTIONNAIRES: Dict[str, List[EligibilityQuestion]] = {
        "PM_KISAN": [
            EligibilityQuestion(
                id="is_landholding_farmer",
                label="Do you or your family own cultivable agricultural land recorded in state revenue records?",
                type="boolean",
                help_text="Landholding must be in the name of the applicant or family member in the land revenue portal.",
                required=True,
            ),
            EligibilityQuestion(
                id="holds_constitutional_post",
                label="Does any family member currently hold or has previously held a constitutional post (e.g. Minister, MP, MLA, Mayor)?",
                type="boolean",
                help_text="Constitutional post holders are statutorily excluded.",
                required=True,
            ),
            EligibilityQuestion(
                id="is_income_tax_payer",
                label="Did any family member pay income tax in the last assessment year?",
                type="boolean",
                help_text="Income tax payers are excluded under PM-KISAN guidelines.",
                required=True,
            ),
            EligibilityQuestion(
                id="is_government_employee",
                label="Is any family member a serving or retired government / PSU employee (excluding Multi-Tasking Staff / Group D)?",
                type="boolean",
                help_text="Regular government employees are disqualified. Class IV / MTS workers are eligible.",
                required=True,
            ),
            EligibilityQuestion(
                id="monthly_pension_over_10k",
                label="Is any retired family member receiving a monthly pension of Rs. 10,000 or more (excluding Group D / MTS)?",
                type="boolean",
                help_text="Pensioners with >= Rs. 10,000/month pension are excluded.",
                required=False,
            ),
        ],
        "AYUSHMAN_BHARAT": [
            EligibilityQuestion(
                id="is_senior_citizen_70_plus",
                label="Is the beneficiary aged 70 years or older?",
                type="boolean",
                help_text="All senior citizens aged 70+ qualify under the Ayushman Vay Vandana expansion regardless of income.",
                required=True,
            ),
            EligibilityQuestion(
                id="in_secc_rural_or_urban_deprived",
                label="Is your household recognized under SECC 2011 deprivation criteria or designated occupational worker categories?",
                type="boolean",
                help_text="Includes rural D1-D7 deprivation households and 11 specified urban worker classes.",
                required=True,
            ),
            EligibilityQuestion(
                id="owns_motorized_vehicle",
                label="Does your household own a motorized 3 or 4 wheeler or mechanized agricultural equipment?",
                type="boolean",
                help_text="Motorized vehicle owners are excluded under standard PM-JAY SECC criteria.",
                required=True,
            ),
            EligibilityQuestion(
                id="is_government_employee",
                label="Is any household member a regular government employee with medical cover?",
                type="boolean",
                help_text="Regular government staff with statutory health coverage are excluded.",
                required=True,
            ),
        ],
        "PMAY_G": [
            EligibilityQuestion(
                id="is_rural_resident",
                label="Do you reside in a rural area?",
                type="boolean",
                help_text="PMAY-G specifically covers rural territories (Gramin).",
                required=True,
            ),
            EligibilityQuestion(
                id="is_houseless_or_kutcha",
                label="Are you houseless or living in a kutcha house (0, 1, or 2 rooms with non-permanent walls/roof)?",
                type="boolean",
                help_text="Verified kutcha housing deprivation is the core qualification basis.",
                required=True,
            ),
            EligibilityQuestion(
                id="owns_pucca_house",
                label="Does any member of your family own a permanent pucca house anywhere in India?",
                type="boolean",
                help_text="Pucca house owners are strictly ineligible.",
                required=True,
            ),
            EligibilityQuestion(
                id="monthly_income_over_15k",
                label="Does any family member earn more than Rs. 15,000 per month or pay income/professional tax?",
                type="boolean",
                help_text="Income threshold is enforced under Awaas+ guidelines.",
                required=True,
            ),
            EligibilityQuestion(
                id="owns_motorized_vehicle",
                label="Does the household own a motorized 2/3/4 wheeler or agricultural tractor?",
                type="boolean",
                help_text="Motor vehicle ownership constitutes a statutory exclusion.",
                required=True,
            ),
        ],
        "NSP_CSSS": [
            EligibilityQuestion(
                id="class_12_percentile_above_80",
                label="Did you score above the 80th percentile in your Class 12 board examination in your specific stream?",
                type="boolean",
                help_text="Merit cutoff published by the respective State or Central Examination Board.",
                required=True,
            ),
            EligibilityQuestion(
                id="enrolled_regular_degree",
                label="Are you pursuing a regular full-time undergraduate or postgraduate degree course (not correspondence)?",
                type="boolean",
                help_text="Distance, diploma, or correspondence students are not covered.",
                required=True,
            ),
            EligibilityQuestion(
                id="annual_family_income",
                label="What is your gross annual family income in INR?",
                type="number",
                help_text="Must not exceed Rs. 4,50,000 per annum.",
                required=True,
            ),
            EligibilityQuestion(
                id="receives_other_scholarship",
                label="Are you currently receiving any other Central or State government scholarship?",
                type="boolean",
                help_text="Students holding another scholarship cannot avail double benefits.",
                required=True,
            ),
        ],
        "TELANGANA_RYTHU_BANDHU": [
            EligibilityQuestion(
                id="is_telangana_resident",
                label="Are you a resident farmer of Telangana State?",
                type="boolean",
                help_text="Scheme is restricted to resident cultivators within Telangana.",
                required=True,
            ),
            EligibilityQuestion(
                id="has_dharani_pattadar_passbook",
                label="Do you hold a digital Title Deed Pattadar Passbook recorded in the Dharani portal?",
                type="boolean",
                help_text="Possession of an official Dharani electronic Pattadar Passbook is mandatory.",
                required=True,
            ),
            EligibilityQuestion(
                id="is_cultivable_agricultural_land",
                label="Is the land extent cultivable agricultural land (not non-agricultural or converted plot)?",
                type="boolean",
                help_text="Commercial, real estate layouts, and barren non-cultivable lands are excluded.",
                required=True,
            ),
        ],
    }

    def get_questions_for_scheme(
        self, scheme_id: str, language: str = "en"
    ) -> EligibilityQuestionsResponse:
        """Return the scheme-specific questionnaire, localized in target language."""
        scheme = scheme_repository.get_by_id(scheme_id)
        if not scheme:
            raise NotFoundError(f"Scheme with ID '{scheme_id}' was not found.")

        questions = questionnaire_mapping_service.get_questionnaire(
            scheme.scheme_id, language=language
        )
        return EligibilityQuestionsResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            questions=questions,
        )

    def evaluate_eligibility(
        self, scheme_id: str, applicant_data: Dict[str, Any]
    ) -> EligibilityEvaluationResponse:
        """Deterministically evaluate applicant answers against scheme rules."""
        scheme = scheme_repository.get_by_id(scheme_id)
        if not scheme:
            raise NotFoundError(f"Scheme with ID '{scheme_id}' was not found.")

        normalized_id = scheme.scheme_id.upper()
        evaluator_method = getattr(self, f"_eval_{normalized_id.lower()}", None)

        if not evaluator_method:
            raise NotFoundError(f"Evaluation rules for '{scheme_id}' are not configured.")

        return evaluator_method(scheme, applicant_data)

    # ------------------ SCHEME-SPECIFIC EVALUATORS ------------------

    def _eval_pm_kisan(self, scheme, data: Dict[str, Any]) -> EligibilityEvaluationResponse:
        results: List[EligibilityConditionResult] = []
        missing: List[str] = []

        # 1. Landholding
        is_farmer = data.get("is_landholding_farmer")
        if is_farmer is True:
            results.append(
                EligibilityConditionResult(
                    condition="Ownership of cultivable landholding in revenue records",
                    status="MET",
                    explanation="Applicant confirmed holding cultivable agricultural land.",
                )
            )
        elif is_farmer is False:
            results.append(
                EligibilityConditionResult(
                    condition="Ownership of cultivable landholding in revenue records",
                    status="NOT_MET",
                    explanation="Landless farmers or non-landholding families are not eligible under PM-KISAN.",
                )
            )
        else:
            missing.append("is_landholding_farmer")
            results.append(
                EligibilityConditionResult(
                    condition="Ownership of cultivable landholding in revenue records",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # 2. Constitutional Post Exclusion
        const_post = data.get("holds_constitutional_post")
        if const_post is False:
            results.append(
                EligibilityConditionResult(
                    condition="Non-holding of constitutional offices",
                    status="MET",
                    explanation="Applicant and family members do not hold constitutional offices.",
                )
            )
        elif const_post is True:
            results.append(
                EligibilityConditionResult(
                    condition="Non-holding of constitutional offices",
                    status="NOT_MET",
                    explanation="Constitutional post holders are statutorily disqualified.",
                )
            )
        else:
            missing.append("holds_constitutional_post")
            results.append(
                EligibilityConditionResult(
                    condition="Non-holding of constitutional offices",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # 3. Income Tax Exclusion
        tax_payer = data.get("is_income_tax_payer")
        if tax_payer is False:
            results.append(
                EligibilityConditionResult(
                    condition="Non-payment of income tax in last assessment year",
                    status="MET",
                    explanation="No family member paid income tax in the last assessment year.",
                )
            )
        elif tax_payer is True:
            results.append(
                EligibilityConditionResult(
                    condition="Non-payment of income tax in last assessment year",
                    status="NOT_MET",
                    explanation="Income tax payers are explicitly excluded from PM-KISAN benefits.",
                )
            )
        else:
            missing.append("is_income_tax_payer")
            results.append(
                EligibilityConditionResult(
                    condition="Non-payment of income tax in last assessment year",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # 4. Government Employee Exclusion
        govt_emp = data.get("is_government_employee")
        if govt_emp is False:
            results.append(
                EligibilityConditionResult(
                    condition="No regular government employment in family (excluding Class IV / MTS)",
                    status="MET",
                    explanation="Family does not have regular government / PSU officers.",
                )
            )
        elif govt_emp is True:
            results.append(
                EligibilityConditionResult(
                    condition="No regular government employment in family (excluding Class IV / MTS)",
                    status="NOT_MET",
                    explanation="Serving or retired regular government employees are excluded.",
                )
            )
        else:
            missing.append("is_government_employee")
            results.append(
                EligibilityConditionResult(
                    condition="No regular government employment in family (excluding Class IV / MTS)",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # Determine overall result
        has_not_met = any(r.status == "NOT_MET" for r in results)
        has_unknown = any(r.status == "UNKNOWN" for r in results)

        if has_not_met:
            overall = "LIKELY_NOT_ELIGIBLE"
        elif has_unknown:
            overall = "NEEDS_MORE_INFORMATION"
        else:
            overall = "LIKELY_ELIGIBLE"

        return EligibilityEvaluationResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            overall_result=overall,
            conditions=results,
            missing_information=missing,
            official_source_url=scheme.official_source_url,
        )

    def _eval_ayushman_bharat(self, scheme, data: Dict[str, Any]) -> EligibilityEvaluationResponse:
        results: List[EligibilityConditionResult] = []
        missing: List[str] = []

        is_senior_70 = data.get("is_senior_citizen_70_plus")
        secc_deprived = data.get("in_secc_rural_or_urban_deprived")
        motor_vehicle = data.get("owns_motorized_vehicle")
        govt_emp = data.get("is_government_employee")

        # Senior citizen route bypasses regular SECC exclusions under 2024 Ayushman Vay Vandana rule
        if is_senior_70 is True:
            results.append(
                EligibilityConditionResult(
                    condition="Senior Citizen 70+ Ayushman Vay Vandana Category",
                    status="MET",
                    explanation="Citizens aged 70 and above receive Rs. 5 lakh top-up health cover regardless of economic status.",
                )
            )
            overall = "LIKELY_ELIGIBLE"
            return EligibilityEvaluationResponse(
                scheme_id=scheme.scheme_id,
                scheme_name=scheme.scheme_name,
                overall_result=overall,
                conditions=results,
                missing_information=[],
                official_source_url=scheme.official_source_url,
            )

        # SECC Route
        if secc_deprived is True:
            results.append(
                EligibilityConditionResult(
                    condition="SECC 2011 deprivation or occupational qualification",
                    status="MET",
                    explanation="Household satisfies designated socio-economic deprivation norms.",
                )
            )
        elif secc_deprived is False:
            results.append(
                EligibilityConditionResult(
                    condition="SECC 2011 deprivation or occupational qualification",
                    status="NOT_MET",
                    explanation="Household is not listed in the SECC 2011 vulnerable database.",
                )
            )
        else:
            missing.append("in_secc_rural_or_urban_deprived")
            results.append(
                EligibilityConditionResult(
                    condition="SECC 2011 deprivation or occupational qualification",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # Vehicle Exclusion
        if motor_vehicle is False:
            results.append(
                EligibilityConditionResult(
                    condition="Absence of motorized vehicle ownership",
                    status="MET",
                    explanation="Household does not own motorized 3/4 wheelers.",
                )
            )
        elif motor_vehicle is True:
            results.append(
                EligibilityConditionResult(
                    condition="Absence of motorized vehicle ownership",
                    status="NOT_MET",
                    explanation="Ownership of motorized 3/4 wheelers disqualifies standard PM-JAY inclusion.",
                )
            )
        else:
            missing.append("owns_motorized_vehicle")
            results.append(
                EligibilityConditionResult(
                    condition="Absence of motorized vehicle ownership",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        # Government Employee Exclusion
        if govt_emp is False:
            results.append(
                EligibilityConditionResult(
                    condition="Non-government employee status",
                    status="MET",
                    explanation="No family member is a regular government employee with state healthcare.",
                )
            )
        elif govt_emp is True:
            results.append(
                EligibilityConditionResult(
                    condition="Non-government employee status",
                    status="NOT_MET",
                    explanation="Regular government employees are covered under dedicated state schemes (CGHS/EHS) and excluded from PM-JAY.",
                )
            )
        else:
            missing.append("is_government_employee")
            results.append(
                EligibilityConditionResult(
                    condition="Non-government employee status",
                    status="UNKNOWN",
                    explanation="Information not provided.",
                )
            )

        has_not_met = any(r.status == "NOT_MET" for r in results)
        has_unknown = any(r.status == "UNKNOWN" for r in results)

        if has_not_met:
            overall = "LIKELY_NOT_ELIGIBLE"
        elif has_unknown:
            overall = "NEEDS_MORE_INFORMATION"
        else:
            overall = "LIKELY_ELIGIBLE"

        return EligibilityEvaluationResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            overall_result=overall,
            conditions=results,
            missing_information=missing,
            official_source_url=scheme.official_source_url,
        )

    def _eval_pmay_g(self, scheme, data: Dict[str, Any]) -> EligibilityEvaluationResponse:
        results: List[EligibilityConditionResult] = []
        missing: List[str] = []

        # Rural residency
        rural = data.get("is_rural_resident")
        if rural is True:
            results.append(EligibilityConditionResult(condition="Rural residency", status="MET", explanation="Resides in rural territory."))
        elif rural is False:
            results.append(EligibilityConditionResult(condition="Rural residency", status="NOT_MET", explanation="PMAY-G covers rural areas only. Urban residents must explore PMAY-U."))
        else:
            missing.append("is_rural_resident")
            results.append(EligibilityConditionResult(condition="Rural residency", status="UNKNOWN", explanation="Missing information."))

        # Kutcha/houseless
        kutcha = data.get("is_houseless_or_kutcha")
        if kutcha is True:
            results.append(EligibilityConditionResult(condition="Houseless or kutcha housing status", status="MET", explanation="Applicant resides in kutcha / non-permanent dwelling."))
        elif kutcha is False:
            results.append(EligibilityConditionResult(condition="Houseless or kutcha housing status", status="NOT_MET", explanation="Living in a non-deprived dwelling."))
        else:
            missing.append("is_houseless_or_kutcha")
            results.append(EligibilityConditionResult(condition="Houseless or kutcha housing status", status="UNKNOWN", explanation="Missing information."))

        # Owns Pucca House
        pucca = data.get("owns_pucca_house")
        if pucca is False:
            results.append(EligibilityConditionResult(condition="No pucca house owned across India", status="MET", explanation="No member owns a permanent pucca house."))
        elif pucca is True:
            results.append(EligibilityConditionResult(condition="No pucca house owned across India", status="NOT_MET", explanation="Families owning a pucca house are disqualified."))
        else:
            missing.append("owns_pucca_house")
            results.append(EligibilityConditionResult(condition="No pucca house owned across India", status="UNKNOWN", explanation="Missing information."))

        # Income limit
        income_high = data.get("monthly_income_over_15k")
        if income_high is False:
            results.append(EligibilityConditionResult(condition="Monthly income not exceeding Rs. 15,000", status="MET", explanation="Income falls within rural deprivation threshold."))
        elif income_high is True:
            results.append(EligibilityConditionResult(condition="Monthly income not exceeding Rs. 15,000", status="NOT_MET", explanation="Monthly income > Rs. 15,000 triggers exclusion."))
        else:
            missing.append("monthly_income_over_15k")
            results.append(EligibilityConditionResult(condition="Monthly income not exceeding Rs. 15,000", status="UNKNOWN", explanation="Missing information."))

        has_not_met = any(r.status == "NOT_MET" for r in results)
        has_unknown = any(r.status == "UNKNOWN" for r in results)

        if has_not_met:
            overall = "LIKELY_NOT_ELIGIBLE"
        elif has_unknown:
            overall = "NEEDS_MORE_INFORMATION"
        else:
            overall = "LIKELY_ELIGIBLE"

        return EligibilityEvaluationResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            overall_result=overall,
            conditions=results,
            missing_information=missing,
            official_source_url=scheme.official_source_url,
        )

    def _eval_nsp_csss(self, scheme, data: Dict[str, Any]) -> EligibilityEvaluationResponse:
        results: List[EligibilityConditionResult] = []
        missing: List[str] = []

        percentile = data.get("class_12_percentile_above_80")
        if percentile is True:
            results.append(EligibilityConditionResult(condition="Above 80th percentile in Class 12 board exam", status="MET", explanation="Scored above 80th percentile merit cutoff."))
        elif percentile is False:
            results.append(EligibilityConditionResult(condition="Above 80th percentile in Class 12 board exam", status="NOT_MET", explanation="Minimum 80th percentile in board stream is mandatory."))
        else:
            missing.append("class_12_percentile_above_80")
            results.append(EligibilityConditionResult(condition="Above 80th percentile in Class 12 board exam", status="UNKNOWN", explanation="Missing percentile score."))

        regular = data.get("enrolled_regular_degree")
        if regular is True:
            results.append(EligibilityConditionResult(condition="Regular full-time degree enrollment", status="MET", explanation="Enrolled in recognized regular college/university."))
        elif regular is False:
            results.append(EligibilityConditionResult(condition="Regular full-time degree enrollment", status="NOT_MET", explanation="Correspondence or diploma courses are excluded."))
        else:
            missing.append("enrolled_regular_degree")
            results.append(EligibilityConditionResult(condition="Regular full-time degree enrollment", status="UNKNOWN", explanation="Missing enrollment status."))

        income = data.get("annual_family_income")
        if income is not None:
            try:
                num_income = float(income)
                if num_income <= 450000:
                    results.append(EligibilityConditionResult(condition="Annual parental income <= Rs. 4,50,000", status="MET", explanation=f"Annual income of Rs. {num_income:,.0f} is within ceiling."))
                else:
                    results.append(EligibilityConditionResult(condition="Annual parental income <= Rs. 4,50,000", status="NOT_MET", explanation=f"Annual income of Rs. {num_income:,.0f} exceeds the Rs. 4.5 lakh ceiling."))
            except ValueError:
                missing.append("annual_family_income")
                results.append(EligibilityConditionResult(condition="Annual parental income <= Rs. 4,50,000", status="UNKNOWN", explanation="Invalid income format."))
        else:
            missing.append("annual_family_income")
            results.append(EligibilityConditionResult(condition="Annual parental income <= Rs. 4,50,000", status="UNKNOWN", explanation="Income not provided."))

        other_sch = data.get("receives_other_scholarship")
        if other_sch is False:
            results.append(EligibilityConditionResult(condition="No concurrent scholarship received", status="MET", explanation="Not availing duplicate government scholarships."))
        elif other_sch is True:
            results.append(EligibilityConditionResult(condition="No concurrent scholarship received", status="NOT_MET", explanation="Simultaneous availing of another scholarship is disallowed."))
        else:
            missing.append("receives_other_scholarship")
            results.append(EligibilityConditionResult(condition="No concurrent scholarship received", status="UNKNOWN", explanation="Missing scholarship information."))

        has_not_met = any(r.status == "NOT_MET" for r in results)
        has_unknown = any(r.status == "UNKNOWN" for r in results)

        if has_not_met:
            overall = "LIKELY_NOT_ELIGIBLE"
        elif has_unknown:
            overall = "NEEDS_MORE_INFORMATION"
        else:
            overall = "LIKELY_ELIGIBLE"

        return EligibilityEvaluationResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            overall_result=overall,
            conditions=results,
            missing_information=missing,
            official_source_url=scheme.official_source_url,
        )

    def _eval_telangana_rythu_bandhu(self, scheme, data: Dict[str, Any]) -> EligibilityEvaluationResponse:
        results: List[EligibilityConditionResult] = []
        missing: List[str] = []

        residency = data.get("is_telangana_resident")
        if residency is True:
            results.append(EligibilityConditionResult(condition="Telangana state resident farmer", status="MET", explanation="Applicant resides in Telangana."))
        elif residency is False:
            results.append(EligibilityConditionResult(condition="Telangana state resident farmer", status="NOT_MET", explanation="Scheme is strictly restricted to resident cultivators of Telangana."))
        else:
            missing.append("is_telangana_resident")
            results.append(EligibilityConditionResult(condition="Telangana state resident farmer", status="UNKNOWN", explanation="Residency not confirmed."))

        passbook = data.get("has_dharani_pattadar_passbook")
        if passbook is True:
            results.append(EligibilityConditionResult(condition="Dharani Title Deed Pattadar Passbook possession", status="MET", explanation="Holds active e-Pattadar Passbook recorded in Dharani portal."))
        elif passbook is False:
            results.append(EligibilityConditionResult(condition="Dharani Title Deed Pattadar Passbook possession", status="NOT_MET", explanation="Possession of an active digital Pattadar Passbook is mandatory."))
        else:
            missing.append("has_dharani_pattadar_passbook")
            results.append(EligibilityConditionResult(condition="Dharani Title Deed Pattadar Passbook possession", status="UNKNOWN", explanation="Passbook information missing."))

        cultivable = data.get("is_cultivable_agricultural_land")
        if cultivable is True:
            results.append(EligibilityConditionResult(condition="Cultivable agricultural land classification", status="MET", explanation="Land is cultivable agricultural acreage."))
        elif cultivable is False:
            results.append(EligibilityConditionResult(condition="Cultivable agricultural land classification", status="NOT_MET", explanation="Non-agricultural, commercial, or residential plots are excluded."))
        else:
            missing.append("is_cultivable_agricultural_land")
            results.append(EligibilityConditionResult(condition="Cultivable agricultural land classification", status="UNKNOWN", explanation="Land type missing."))

        has_not_met = any(r.status == "NOT_MET" for r in results)
        has_unknown = any(r.status == "UNKNOWN" for r in results)

        if has_not_met:
            overall = "LIKELY_NOT_ELIGIBLE"
        elif has_unknown:
            overall = "NEEDS_MORE_INFORMATION"
        else:
            overall = "LIKELY_ELIGIBLE"

        return EligibilityEvaluationResponse(
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            overall_result=overall,
            conditions=results,
            missing_information=missing,
            official_source_url=scheme.official_source_url,
        )


# Default evaluation service instance
eligibility_service = EligibilityEvaluationService()

"""Questionnaire Definition & Scheme Mapping Service for NitiSetu.

Converts verified scheme eligibility and exclusion criteria into structured,
criterion-specific QuestionnaireItem instances supporting multilingual presentation
(English, Telugu, Hindi) and deterministic evaluation compatibility.
"""

from typing import Any, Dict, List, Literal, Optional
from app.core.exceptions import NotFoundError
from app.repositories.scheme_repository import scheme_repository
from app.schemas.chat_query_schema import PendingQuestion
from app.schemas.eligibility_schemas import (
    CriterionValidationRule,
    QuestionnaireItem,
)
from app.schemas.scheme_schemas import EligibilityQuestion


class QuestionnaireMappingService:
    """Service providing canonical questionnaire mapping for welfare schemes.

    Features:
    - Binds citizen-facing questions to verified scheme criteria in schemes.json.
    - Enforces stable criterion_id and question_id across all languages.
    - Supports input types: boolean, number, select, text, date.
    - Emits criterion-specific validation rules.
    - Renders localized prompts for English (en), Telugu (te), and Hindi (hi).
    """

    SUPPORTED_LANGUAGES = ("en", "te", "hi")

    # Raw definition specifications for all 5 verified schemes
    SCHEME_SPECS: Dict[str, List[Dict[str, Any]]] = {
        "PM_KISAN": [
            {
                "id": "is_landholding_farmer",
                "criterion_id": "is_landholding_farmer",
                "type": "boolean",
                "required": True,
                "order": 1,
                "category": "landholding",
                "condition_type": "eligibility",
                "scheme_condition": "The farmer family (husband, wife, and minor children) must own cultivable agricultural land as per official state land revenue records.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_landholding_farmer",
                    input_type="boolean",
                    error_message="Please confirm whether you or your family owns cultivable agricultural land.",
                    clarification_hint="Land must be registered in the state revenue portal in the name of the applicant or family member.",
                ),
                "translations": {
                    "en": {
                        "label": "Do you or your family own cultivable agricultural land recorded in state revenue records?",
                        "help_text": "Landholding must be in the name of the applicant or family member in the land revenue portal.",
                    },
                    "te": {
                        "label": "మీకు లేదా మీ కుటుంబానికి రెవెన్యూ రికార్డులలో నమోదైన సాగు భూమి ఉందా?",
                        "help_text": "భూమి యజమాని వివరాలు రాష్ట్ర భూ రికార్డుల పోర్టల్‌లో నమోదై ఉండాలి.",
                    },
                    "hi": {
                        "label": "क्या आपके या आपके परिवार के पास राज्य राजस्व रिकॉर्ड में दर्ज कृषि योग्य भूमि है?",
                        "help_text": "भूमि का स्वामित्व राज्य के भू-अभिलेख पोर्टल में आवेदक या परिवार के सदस्य के नाम होना चाहिए।",
                    },
                },
            },
            {
                "id": "holds_constitutional_post",
                "criterion_id": "holds_constitutional_post",
                "type": "boolean",
                "required": True,
                "order": 2,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Farmer families where any member holds or held constitutional posts (e.g. President, Vice President, Governors, Ministers, MPs, MLAs, Mayors).",
                "validation_rule": CriterionValidationRule(
                    criterion_id="holds_constitutional_post",
                    input_type="boolean",
                    error_message="Please answer Yes or No regarding constitutional post holding.",
                    clarification_hint="Constitutional post holders are statutorily disqualified from PM-KISAN.",
                ),
                "translations": {
                    "en": {
                        "label": "Does any family member currently hold or has previously held a constitutional post (e.g. Minister, MP, MLA, Mayor)?",
                        "help_text": "Constitutional post holders are statutorily excluded.",
                    },
                    "te": {
                        "label": "మీ కుటుంబంలో ఎవరైనా రాజ్యాంగ పదవిని (ఉదా. మంత్రి, ఎంపీ, ఎమ్మెల్యే, మేయర్) నిర్వహిస్తున్నారా లేదా గతంలో నిర్వహించారా?",
                        "help_text": "రాజ్యాంగ పదవులు నిర్వహించిన వారు లేదా నిర్వహిస్తున్న వారు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या परिवार का कोई सदस्य वर्तमान में या पहले किसी संवैधानिक पद (जैसे मंत्री, सांसद, विधायक, मेयर) पर रहा है?",
                        "help_text": "संवैधानिक पद धारक वैधानिक रूप से इस योजना से बाहर हैं।",
                    },
                },
            },
            {
                "id": "is_government_employee",
                "criterion_id": "is_government_employee",
                "type": "boolean",
                "required": True,
                "order": 3,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Serving or retired officers and employees of Central/State Government Ministries, Departments, or PSUs (excluding Multi-Tasking Staff / Group D / Class IV).",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_government_employee",
                    input_type="boolean",
                    error_message="Please indicate whether any family member is a regular government employee.",
                    clarification_hint="Class IV, MTS, and Group D employees are exempted and remain eligible.",
                ),
                "translations": {
                    "en": {
                        "label": "Is any family member a serving or retired government / PSU employee (excluding Multi-Tasking Staff / Group D)?",
                        "help_text": "Regular government employees are disqualified. Class IV / MTS workers are eligible.",
                    },
                    "te": {
                        "label": "మీ కుటుంబంలో ఎవరైనా ప్రభుత్వం లేదా ప్రభుత్వ రంగ సంస్థలో (పీఎస్‌యూ) ఉద్యోగిగా పనిచేస్తున్నారా లేదా రిటైర్ అయ్యారా (గ్రూప్-డి / ఎంటీఎస్ మినహా)?",
                        "help_text": "రెగ్యులర్ ప్రభుత్వ ఉద్యోగులు అర్హులు కారు. గ్రూప్-డి/ఎంటీఎస్ ఉద్యోగులు అర్హులు.",
                    },
                    "hi": {
                        "label": "क्या परिवार का कोई सदस्य सरकारी या पीएसयू का सेवारत या सेवानिवृत्त कर्मचारी है (मल्टी-टास्किंग स्टाफ/ग्रुप डी को छोड़कर)?",
                        "help_text": "नियमित सरकारी कर्मचारी अपात्र हैं। चतुर्थ श्रेणी/एमटीएस कर्मचारी पात्र हैं।",
                    },
                },
            },
            {
                "id": "is_income_tax_payer",
                "criterion_id": "is_income_tax_payer",
                "type": "boolean",
                "required": True,
                "order": 4,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "All persons who paid income tax in the last assessment year.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_income_tax_payer",
                    input_type="boolean",
                    error_message="Please confirm whether any family member paid income tax in the last assessment year.",
                    clarification_hint="Income tax payers are excluded under statutory PM-KISAN guidelines.",
                ),
                "translations": {
                    "en": {
                        "label": "Did any family member pay income tax in the last assessment year?",
                        "help_text": "Income tax payers are excluded under PM-KISAN guidelines.",
                    },
                    "te": {
                        "label": "గత అసెస్‌మెంట్ సంవత్సరంలో మీ కుటుంబంలో ఎవరైనా ఆదాయపు పన్ను (ఇన్‌కమ్ ట్యాక్స్) చెల్లించారా?",
                        "help_text": "పీఎం-కిసాన్ మార్గదర్శకాల ప్రకారం ఆదాయపు పన్ను చెల్లించేవారు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या पिछले निर्धारण वर्ष में परिवार के किसी सदस्य ने आयकर (Income Tax) का भुगतान किया था?",
                        "help_text": "पीएम-किसान दिशानिर्देशों के तहत आयकर दाता अपात्र हैं।",
                    },
                },
            },
            {
                "id": "monthly_pension_over_10k",
                "criterion_id": "monthly_pension_over_10k",
                "type": "boolean",
                "required": False,
                "order": 5,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "All superannuated / retired pensioners whose monthly pension is Rs. 10,000 or more (excluding Group D / MTS).",
                "validation_rule": CriterionValidationRule(
                    criterion_id="monthly_pension_over_10k",
                    input_type="boolean",
                    error_message="Please specify if any retired member receives >= Rs. 10,000/month pension.",
                ),
                "translations": {
                    "en": {
                        "label": "Is any retired family member receiving a monthly pension of Rs. 10,000 or more (excluding Group D / MTS)?",
                        "help_text": "Pensioners with >= Rs. 10,000/month pension are excluded.",
                    },
                    "te": {
                        "label": "రిటైర్ అయిన మీ కుటుంబ సభ్యులలో ఎవరికైనా నెలకు రూ. 10,000 లేదా అంతకంటే ఎక్కువ పెన్షన్ వస్తుందా (గ్రూప్-డి / ఎంటీఎస్ మినహా)?",
                        "help_text": "నెలకు రూ. 10,000 లేదా అంతకంటే ఎక్కువ పెన్షన్ పొందే పెన్షనర్లు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या परिवार का कोई सेवानिवृत्त सदस्य ₹10,000 या अधिक की मासिक पेंशन प्राप्त कर रहा है (ग्रुप डी/एमटीएस को छोड़कर)?",
                        "help_text": "₹10,000/माह या अधिक पेंशन पाने वाले पेंशनभोगी अपात्र हैं।",
                    },
                },
            },
        ],
        "AYUSHMAN_BHARAT": [
            {
                "id": "is_senior_citizen_70_plus",
                "criterion_id": "is_senior_citizen_70_plus",
                "type": "boolean",
                "required": True,
                "order": 1,
                "category": "demographic",
                "condition_type": "eligibility",
                "scheme_condition": "OR any individual aged 70 years and above (under the Senior Citizen Ayushman Vay Vandana sub-scheme).",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_senior_citizen_70_plus",
                    input_type="boolean",
                    error_message="Please answer Yes or No for senior citizen (70+) status.",
                    clarification_hint="Citizens aged 70+ receive comprehensive health coverage regardless of income.",
                ),
                "translations": {
                    "en": {
                        "label": "Is the beneficiary aged 70 years or older?",
                        "help_text": "All senior citizens aged 70+ qualify under the Ayushman Vay Vandana expansion regardless of income.",
                    },
                    "te": {
                        "label": "లబ్ధిదారుడి వయస్సు 70 సంవత్సరాలు లేదా అంతకంటే ఎక్కువ ఉందా?",
                        "help_text": "ఆయుష్మాన్ వయ వందన పథకం కింద 70 ఏళ్లు పైబడిన సీనియర్ సిటిజన్లు అందరూ ఆదాయంతో సంబంధం లేకుండా అర్హులు.",
                    },
                    "hi": {
                        "label": "क्या लाभार्थी की आयु 70 वर्ष या उससे अधिक है?",
                        "help_text": "आयुष्मान वय वंदना योजना के तहत 70+ आयु के सभी वरिष्ठ नागरिक आय की परवाह किए बिना पात्र हैं।",
                    },
                },
            },
            {
                "id": "in_secc_rural_or_urban_deprived",
                "criterion_id": "in_secc_rural_or_urban_deprived",
                "type": "boolean",
                "required": True,
                "order": 2,
                "category": "deprivation",
                "condition_type": "eligibility",
                "scheme_condition": "Rural households satisfying SECC 2011 deprivation criteria... OR Urban households belonging to 11 occupational categories.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="in_secc_rural_or_urban_deprived",
                    input_type="boolean",
                    error_message="Please confirm whether your household satisfies SECC 2011 deprivation criteria.",
                ),
                "translations": {
                    "en": {
                        "label": "Is your household recognized under SECC 2011 deprivation criteria or designated occupational worker categories?",
                        "help_text": "Includes rural D1-D7 deprivation households and 11 specified urban worker classes.",
                    },
                    "te": {
                        "label": "మీ కుటుంబం ఎస్ఈసీసీ 2011 పేదరిక వర్గీకరణలో లేదా నిర్దేశిత కార్మిక వర్గాలలో నమోదై ఉందా?",
                        "help_text": "గ్రామీణ D1-D7 నిరుపేద కుటుంబాలు మరియు 11 నిర్దిష్ట పట్టణ కార్మిక వర్గాలు ఇందులో చేర్చబడ్డాయి.",
                    },
                    "hi": {
                        "label": "क्या आपका परिवार एसईसीसी 2011 वंचितता मानदंड या निर्धारित व्यावसायिक श्रमिक श्रेणियों के तहत आता है?",
                        "help_text": "ग्रामीण D1-D7 वंचित परिवार और 11 निर्दिष्ट शहरी श्रमिक श्रेणियां इसमें शामिल हैं।",
                    },
                },
            },
            {
                "id": "owns_motorized_vehicle",
                "criterion_id": "owns_motorized_vehicle",
                "type": "boolean",
                "required": True,
                "order": 3,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Households owning motorized 2/3/4 wheelers or fishing boats with motors.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="owns_motorized_vehicle",
                    input_type="boolean",
                    error_message="Please answer Yes or No regarding motorized vehicle ownership.",
                ),
                "translations": {
                    "en": {
                        "label": "Does your household own a motorized 3 or 4 wheeler or mechanized agricultural equipment?",
                        "help_text": "Motorized vehicle owners are excluded under standard PM-JAY SECC criteria.",
                    },
                    "te": {
                        "label": "మీ కుటుంబానికి 3 లేదా 4 చక్రాల మోటారు వాహనం లేదా యాంత్రిక వ్యవసాయ పరికరాలు ఉన్నాయా?",
                        "help_text": "మోటారు వాహనాలు ఉన్న కుటుంబాలు సాధారణ పీఎం-జేవై నిబంధనల ప్రకారం అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या आपके परिवार के पास तिपहिया/चौपहिया मोटर चालित वाहन या मशीनीकृत कृषि उपकरण हैं?",
                        "help_text": "मानक पीएम-जेएवाई एसईसीसी मानदंडों के तहत मोटर वाहन मालिक अपात्र हैं।",
                    },
                },
            },
            {
                "id": "is_government_employee",
                "criterion_id": "is_government_employee",
                "type": "boolean",
                "required": True,
                "order": 4,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Households with any family member who is a regular government employee.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_government_employee",
                    input_type="boolean",
                    error_message="Please confirm whether any member is a regular government employee.",
                ),
                "translations": {
                    "en": {
                        "label": "Is any household member a regular government employee with medical cover?",
                        "help_text": "Regular government staff with statutory health coverage are excluded.",
                    },
                    "te": {
                        "label": "మీ కుటుంబంలో ఎవరైనా ప్రభుత్వ ఆరోగ్య పథకం పొందే రెగ్యులర్ ప్రభుత్వ ఉద్యోగిగా ఉన్నారా?",
                        "help_text": "ప్రభుత్వ ఆరోగ్య రక్షణ ఉన్న రెగ్యులర్ ప్రభుత్వ ఉద్యోగులు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या परिवार का कोई सदस्य स्वास्थ्य कवर वाला नियमित सरकारी कर्मचारी है?",
                        "help_text": "वैधानिक स्वास्थ्य कवरेज वाले नियमित सरकारी कर्मचारी अपात्र हैं।",
                    },
                },
            },
        ],
        "PMAY_G": [
            {
                "id": "is_rural_resident",
                "criterion_id": "is_rural_resident",
                "type": "boolean",
                "required": True,
                "order": 1,
                "category": "residency",
                "condition_type": "eligibility",
                "scheme_condition": "Must be a rural resident family.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_rural_resident",
                    input_type="boolean",
                    error_message="Please confirm whether you reside in a rural area.",
                ),
                "translations": {
                    "en": {
                        "label": "Do you reside in a rural area?",
                        "help_text": "PMAY-G specifically covers rural territories (Gramin).",
                    },
                    "te": {
                        "label": "మీరు గ్రామీణ ప్రాంతంలో నివసిస్తున్నారా?",
                        "help_text": "పీఎంఏవై-జి పథకం ప్రత్యేకంగా గ్రామీణ ప్రాంతాలకు మాత్రమే వర్తిస్తుంది.",
                    },
                    "hi": {
                        "label": "क्या आप ग्रामीण क्षेत्र में निवास करते हैं?",
                        "help_text": "पीएमएवाई-जी विशेष रूप से ग्रामीण क्षेत्रों के लिए है।",
                    },
                },
            },
            {
                "id": "is_houseless_or_kutcha",
                "criterion_id": "is_houseless_or_kutcha",
                "type": "boolean",
                "required": True,
                "order": 2,
                "category": "housing",
                "condition_type": "eligibility",
                "scheme_condition": "The family must be houseless or living in kutcha houses (zero, one, or two rooms with kutcha walls and kutcha roof) as prioritized by SECC 2011 and Awaas+ list.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_houseless_or_kutcha",
                    input_type="boolean",
                    error_message="Please indicate whether you are houseless or living in a kutcha house.",
                ),
                "translations": {
                    "en": {
                        "label": "Are you houseless or living in a kutcha house (0, 1, or 2 rooms with non-permanent walls/roof)?",
                        "help_text": "Verified kutcha housing deprivation is the core qualification basis.",
                    },
                    "te": {
                        "label": "మీకు ఇల్లు లేదా లేదా మట్టిగోడలు/తాటాకులతో కూడిన కచ్చా ఇంట్లో (0, 1, లేదా 2 గదులు) నివసిస్తున్నారా?",
                        "help_text": "కచ్చా ఇల్లు లేదా నివాసం లేకపోవడం ఈ పథకానికి ప్రధాన అర్హత.",
                    },
                    "hi": {
                        "label": "क्या आप बेघर हैं या कच्चे घर (0, 1 या 2 कमरे, कच्ची दीवारें/छत) में रह रहे हैं?",
                        "help_text": "कच्चा मकान या बेघर होना इस योजना का मुख्य पात्रता आधार है।",
                    },
                },
            },
            {
                "id": "owns_pucca_house",
                "criterion_id": "owns_pucca_house",
                "type": "boolean",
                "required": True,
                "order": 3,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Neither the applicant nor any family member must own a pucca permanent house anywhere in India.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="owns_pucca_house",
                    input_type="boolean",
                    error_message="Please confirm whether your family owns a pucca permanent house.",
                ),
                "translations": {
                    "en": {
                        "label": "Does any member of your family own a permanent pucca house anywhere in India?",
                        "help_text": "Pucca house owners are strictly ineligible.",
                    },
                    "te": {
                        "label": "భారతదేశంలో ఎక్కడైనా మీ కుటుంబ సభ్యుల పేరిట శాశ్వత పక్కా ఇల్లు ఉందా?",
                        "help_text": "పక్కా ఇల్లు ఉన్న కుటుంబాలు ఈ పథకానికి అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या भारत में कहीं भी आपके परिवार के किसी सदस्य के पास पक्का मकान है?",
                        "help_text": "पक्के मकान के मालिक इस योजना के लिए पूरी तरह अपात्र हैं।",
                    },
                },
            },
            {
                "id": "monthly_income_over_15k",
                "criterion_id": "monthly_income_over_15k",
                "type": "boolean",
                "required": True,
                "order": 4,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Households with any member earning more than Rs. 15,000 per month / paying tax.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="monthly_income_over_15k",
                    input_type="boolean",
                    error_message="Please confirm whether family monthly earnings exceed Rs. 15,000.",
                ),
                "translations": {
                    "en": {
                        "label": "Does any family member earn more than Rs. 15,000 per month or pay income/professional tax?",
                        "help_text": "Income threshold is enforced under Awaas+ guidelines.",
                    },
                    "te": {
                        "label": "మీ కుటుంబంలో ఎవరైనా నెలకు రూ. 15,000 కంటే ఎక్కువ సంపాదిస్తున్నారా లేదా పన్ను చెల్లిస్తున్నారా?",
                        "help_text": "ఆవాస్+ మార్గదర్శకాల ప్రకారం నెలకు రూ. 15,000 కంటే ఎక్కువ ఆదాయం ఉన్నవారు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या परिवार का कोई सदस्य ₹15,000 प्रति माह से अधिक कमाता है या आयकर/व्यवसाय कर देता है?",
                        "help_text": "आवास+ दिशानिर्देशों के तहत मासिक आय सीमा ₹15,000 लागू है।",
                    },
                },
            },
            {
                "id": "owns_motorized_vehicle",
                "criterion_id": "owns_motorized_vehicle",
                "type": "boolean",
                "required": True,
                "order": 5,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Ownership of motorized two, three, or four-wheelers, or mechanized boats.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="owns_motorized_vehicle",
                    input_type="boolean",
                    error_message="Please confirm motorized vehicle ownership.",
                ),
                "translations": {
                    "en": {
                        "label": "Does the household own a motorized 2/3/4 wheeler or agricultural tractor?",
                        "help_text": "Motor vehicle ownership constitutes a statutory exclusion.",
                    },
                    "te": {
                        "label": "మీ కుటుంబానికి 2/3/4 చక్రాల మోటారు వాహనం లేదా ట్రాక్టర్ ఉందా?",
                        "help_text": "మోటారు వాహనం ఉండటం అనర్హతకు కారణమవుతుంది.",
                    },
                    "hi": {
                        "label": "क्या परिवार के पास दोपहिया/तिपहिया/चौपहिया मोटर वाहन या ट्रैक्टर है?",
                        "help_text": "मोटर वाहन का स्वामित्व वैधानिक अपात्रता का आधार है।",
                    },
                },
            },
        ],
        "NSP_CSSS": [
            {
                "id": "class_12_percentile_above_80",
                "criterion_id": "class_12_percentile_above_80",
                "type": "boolean",
                "required": True,
                "order": 1,
                "category": "academic",
                "condition_type": "eligibility",
                "scheme_condition": "Student must have scored above the 80th percentile in the relevant stream in Class 12 (10+2 pattern) examination from a recognized State/Central Board.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="class_12_percentile_above_80",
                    input_type="boolean",
                    error_message="Please confirm whether you scored above the 80th percentile in Class 12.",
                    clarification_hint="Check your Class 12 passing certificate or official board merit cutoff list.",
                ),
                "translations": {
                    "en": {
                        "label": "Did you score above the 80th percentile in your Class 12 board examination in your specific stream?",
                        "help_text": "Merit cutoff published by the respective State or Central Examination Board.",
                    },
                    "te": {
                        "label": "మీరు 12వ తరగతి (ఇంటర్మీడియట్) బోర్డు పరీక్షలో మీ సబ్జెక్ట్ విభాగంలో 80వ పర్సంటైల్ కంటే ఎక్కువ మార్కులు సాధించారా?",
                        "help_text": "సంబంధిత విద్యా బోర్డు నిర్ణయించిన మెరిట్ కటాఫ్ మార్కులు కలిగి ఉండాలి.",
                    },
                    "hi": {
                        "label": "क्या आपने अपनी संबंधित स्ट्रीम में कक्षा 12वीं की बोर्ड परीक्षा में 80वें पर्सेंटाइल से अधिक अंक प्राप्त किए हैं?",
                        "help_text": "संबंधित राज्य या केंद्रीय परीक्षा बोर्ड द्वारा जारी मेरिट कटऑफ।",
                    },
                },
            },
            {
                "id": "enrolled_regular_degree",
                "criterion_id": "enrolled_regular_degree",
                "type": "boolean",
                "required": True,
                "order": 2,
                "category": "academic",
                "condition_type": "eligibility",
                "scheme_condition": "Must be pursuing regular full-time undergraduate or postgraduate courses in a college or institution recognized by AICTE, UGC, or MCI.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="enrolled_regular_degree",
                    input_type="boolean",
                    error_message="Please confirm whether you are pursuing a full-time regular degree course.",
                ),
                "translations": {
                    "en": {
                        "label": "Are you pursuing a regular full-time undergraduate or postgraduate degree course (not correspondence)?",
                        "help_text": "Distance, diploma, or correspondence students are not covered.",
                    },
                    "te": {
                        "label": "మీరు కళాశాల లేదా విశ్వవిద్యాలయంలో రెగ్యులర్ పూర్తికాల డిగ్రీ లేదా పీజీ కోర్సు చదువుతున్నారా (కరస్పాండెన్స్ కాకుండా)?",
                        "help_text": "దూరవిద్య లేదా డిప్లొమా విద్యార్థులు ఈ స్కాలర్‌షిప్‌కు అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या आप एक नियमित पूर्णकालिक स्नातक या स्नातकोत्तर डिग्री पाठ्यक्रम में नामांकित हैं (दूरस्थ शिक्षा नहीं)?",
                        "help_text": "दूरस्थ शिक्षा, डिप्लोमा या पत्राचार के छात्र शामिल नहीं हैं।",
                    },
                },
            },
            {
                "id": "annual_family_income",
                "criterion_id": "annual_family_income",
                "type": "number",
                "required": True,
                "order": 3,
                "category": "income",
                "condition_type": "eligibility",
                "scheme_condition": "Gross annual parental / family income must not exceed Rs. 4,50,000 per annum.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="annual_family_income",
                    input_type="number",
                    min_value=0.0,
                    max_value=10000000.0,
                    error_message="Please enter a valid gross annual family income in INR (e.g. 250000).",
                    clarification_hint="Gross annual income of both parents from all sources as per Revenue Income Certificate.",
                ),
                "translations": {
                    "en": {
                        "label": "What is your gross annual family income in INR?",
                        "help_text": "Must not exceed Rs. 4,50,000 per annum.",
                    },
                    "te": {
                        "label": "మీ కుటుంబ వార్షిక స్థూల ఆదాయం ఎంత (రూపాయలలో)?",
                        "help_text": "కుటుంబ వార్షిక ఆదాయం రూ. 4,50,000 మించకూడదు.",
                    },
                    "hi": {
                        "label": "आपकी कुल वार्षिक पारिवारिक आय (रुपये में) कितनी है?",
                        "help_text": "वार्षिक पारिवारिक आय ₹4,50,000 से अधिक नहीं होनी चाहिए।",
                    },
                },
            },
            {
                "id": "receives_other_scholarship",
                "criterion_id": "receives_other_scholarship",
                "type": "boolean",
                "required": True,
                "order": 4,
                "category": "exclusion",
                "condition_type": "exclusion",
                "scheme_condition": "Applicant must not be availing of any other state or central scholarship or fee concession.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="receives_other_scholarship",
                    input_type="boolean",
                    error_message="Please confirm whether you are receiving any other government scholarship.",
                ),
                "translations": {
                    "en": {
                        "label": "Are you currently receiving any other Central or State government scholarship?",
                        "help_text": "Students holding another scholarship cannot avail double benefits.",
                    },
                    "te": {
                        "label": "మీరు ప్రస్తుతం కేంద్ర లేదా రాష్ట్ర ప్రభుత్వానికి చెందిన మరేదైనా ఇతర స్కాలర్‌షిప్ పొందుతున్నారా?",
                        "help_text": "ఇప్పటికే వేరే స్కాలర్‌షిప్ పొందుతున్న విద్యార్థులు దీనికి అర్హులు కారు.",
                    },
                    "hi": {
                        "label": "क्या आप वर्तमान में केंद्र या राज्य सरकार की किसी अन्य छात्रवृत्ति का लाभ ले रहे हैं?",
                        "help_text": "अन्य छात्रवृत्ति प्राप्त करने वाले छात्र दोहरा लाभ नहीं ले सकते।",
                    },
                },
            },
        ],
        "TELANGANA_RYTHU_BANDHU": [
            {
                "id": "is_telangana_resident",
                "criterion_id": "is_telangana_resident",
                "type": "boolean",
                "required": True,
                "order": 1,
                "category": "residency",
                "condition_type": "eligibility",
                "scheme_condition": "Applicant must be a permanent resident farmer of Telangana State.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_telangana_resident",
                    input_type="boolean",
                    error_message="Please confirm whether you are a resident farmer of Telangana State.",
                ),
                "translations": {
                    "en": {
                        "label": "Are you a resident farmer of Telangana State?",
                        "help_text": "Scheme is restricted to resident cultivators within Telangana.",
                    },
                    "te": {
                        "label": "మీరు తెలంగాణ రాష్ట్రంలో స్థిర నివాసమున్న రైతులేనా?",
                        "help_text": "ఈ పథకం తెలంగాణ రాష్ట్ర నివాసితులకు మాత్రమే వర్తిస్తుంది.",
                    },
                    "hi": {
                        "label": "क्या आप तेलंगाना राज्य के निवासी किसान हैं?",
                        "help_text": "यह योजना केवल तेलंगाना के निवासी किसानों तक सीमित है।",
                    },
                },
            },
            {
                "id": "has_dharani_pattadar_passbook",
                "criterion_id": "has_dharani_pattadar_passbook",
                "type": "boolean",
                "required": True,
                "order": 2,
                "category": "landholding",
                "condition_type": "eligibility",
                "scheme_condition": "Must be an agricultural land titleholder with an active digital Pattadar Passbook issued through the Dharani portal (e-Pattadar Passbook).",
                "validation_rule": CriterionValidationRule(
                    criterion_id="has_dharani_pattadar_passbook",
                    input_type="boolean",
                    error_message="Please confirm possession of an active Dharani digital Pattadar Passbook.",
                ),
                "translations": {
                    "en": {
                        "label": "Do you hold a digital Title Deed Pattadar Passbook recorded in the Dharani portal?",
                        "help_text": "Possession of an official Dharani electronic Pattadar Passbook is mandatory.",
                    },
                    "te": {
                        "label": "మీకు ధరణి పోర్టల్‌లో నమోదైన డిజిటల్ పట్టాదారు పాస్‌పుస్తకం ఉందా?",
                        "help_text": "ధరణి పోర్టల్ ద్వారా జారీ చేయబడిన ఈ-పట్టాదారు పాస్‌పుస్తకం తప్పనిసరి.",
                    },
                    "hi": {
                        "label": "क्या आपके पास धरणी पोर्टल में दर्ज डिजिटल पट्टादार पासबुक है?",
                        "help_text": "धरणी पोर्टल के माध्यम से आधिकारिक डिजिटल पट्टादार पासबुक का होना अनिवार्य है।",
                    },
                },
            },
            {
                "id": "is_cultivable_agricultural_land",
                "criterion_id": "is_cultivable_agricultural_land",
                "type": "boolean",
                "required": True,
                "order": 3,
                "category": "landholding",
                "condition_type": "eligibility",
                "scheme_condition": "The land must be cultivable agricultural land registered in the revenue department database.",
                "validation_rule": CriterionValidationRule(
                    criterion_id="is_cultivable_agricultural_land",
                    input_type="boolean",
                    error_message="Please confirm that the land is cultivable agricultural acreage.",
                ),
                "translations": {
                    "en": {
                        "label": "Is the land extent cultivable agricultural land (not non-agricultural or converted plot)?",
                        "help_text": "Commercial, real estate layouts, and barren non-cultivable lands are excluded.",
                    },
                    "te": {
                        "label": "మీ భూమి సాగుకు అనుకూలమైన వ్యవసాయ భూమేనా (వ్యవసాయేతర లేదా రియల్ ఎస్టేట్ ప్లాట్లు కాకుండా)?",
                        "help_text": "వాణిజ్య, రియల్ ఎస్టేట్ మరియు సాగుకు అనుకూలం కాని భూములు ఈ పథకం పరిధిలోకి రావు.",
                    },
                    "hi": {
                        "label": "क्या यह भूमि कृषि योग्य भूमि है (गैर-कृषि या रियल एस्टेट प्लॉट नहीं)?",
                        "help_text": "व्यावसायिक, रियल एस्टेट लेआउट और बंजर गैर-कृषि योग्य भूमि बाहर रखी गई है।",
                    },
                },
            },
        ],
    }

    # Administrative and statutory criteria in schemes.json that are NOT queried directly
    # from citizens, accompanied by the architectural and administrative justification.
    UNMAPPED_CRITERIA_REGISTRY: Dict[str, List[Dict[str, str]]] = {
        "PM_KISAN": [
            {
                "condition": "Applicant must be an Indian citizen.",
                "type": "eligibility",
                "reason": "General statutory prerequisite across all central schemes; verified administratively via Aadhaar KYC at application time rather than subjective inquiry.",
            },
            {
                "condition": "Landholding records must be updated in the state land database.",
                "type": "eligibility",
                "reason": "Administrative backend database synchronization requirement verified directly by State Nodal Officers against state land records.",
            },
            {
                "condition": "Bank account must be Aadhaar-linked and active with biometric/eKYC completed.",
                "type": "eligibility",
                "reason": "Direct Benefit Transfer (DBT) disbursement prerequisite fulfilled during onboarding, not a disqualifying eligibility rule.",
            },
            {
                "condition": "Institutional landholders are strictly ineligible.",
                "type": "exclusion",
                "reason": "Legal entity status verified directly on land title deed (titles held by trusts/societies/companies vs natural persons).",
            },
            {
                "condition": "Professionals like Doctors, Engineers, Lawyers, Chartered Accountants, and Architects registered with professional bodies and carrying out practice.",
                "type": "exclusion",
                "reason": "Subsumed under the income tax payer and constitutional/government exclusions in the standard civic assessment.",
            },
        ],
        "AYUSHMAN_BHARAT": [
            {
                "condition": "Households owning mechanized agricultural equipment (tractors/harvesters).",
                "type": "exclusion",
                "reason": "Subsumed directly under the motorized vehicle & mechanized equipment exclusion question.",
            },
            {
                "condition": "Households with non-agricultural enterprises registered with the government.",
                "type": "exclusion",
                "reason": "Administrative SECC database verification item cross-matched with MSME/Udyam registry.",
            },
            {
                "condition": "Households paying professional tax or income tax.",
                "type": "exclusion",
                "reason": "Verified automatically against State Commercial Taxes and CBDT PAN database.",
            },
        ],
        "PMAY_G": [
            {
                "condition": "Having a Kisan Credit Card (KCC) with credit limit of Rs. 50,000 or above.",
                "type": "exclusion",
                "reason": "Awaas+ 13-point exclusion checklist item cross-verified by Gram Sabha and banking database.",
            },
            {
                "condition": "Households with non-agricultural enterprise registered with government.",
                "type": "exclusion",
                "reason": "Enterprise registration verified via Udyam database cross-matching.",
            },
            {
                "condition": "Households with landline phone or owning 2.5 acres or more of irrigated land.",
                "type": "exclusion",
                "reason": "Verified by village revenue officers during field verification and Gram Sabha social audit.",
            },
        ],
        "NSP_CSSS": [
            {
                "condition": "Students scoring below 50% marks in semester renewal examinations or failing attendance norms.",
                "type": "exclusion",
                "reason": "Ongoing renewal milestone required in subsequent academic years; not an initial entry qualification.",
            },
            {
                "condition": "Students pursuing diploma courses, vocational courses, or distance/correspondence education.",
                "type": "exclusion",
                "reason": "Direct inverse of the regular full-time degree enrollment qualification (enrolled_regular_degree).",
            },
        ],
        "TELANGANA_RYTHU_BANDHU": [
            {
                "condition": "Non-agricultural land, real estate layouts, and commercial industrial plots are strictly excluded.",
                "type": "exclusion",
                "reason": "Direct inverse of the cultivable agricultural land classification condition (is_cultivable_agricultural_land).",
            },
            {
                "condition": "Tenant farmers (who do not hold ownership Pattadar titles in their own name) are not covered under Rythu Bandhu directly.",
                "type": "exclusion",
                "reason": "Direct inverse of holding an active digital Dharani Pattadar Passbook (has_dharani_pattadar_passbook).",
            },
            {
                "condition": "Government-owned or forest lands without registered pattadar titles.",
                "type": "exclusion",
                "reason": "Administrative land classification verified directly on the Dharani revenue portal.",
            },
        ],
    }

    def get_questionnaire(
        self, scheme_id: str, language: str = "en"
    ) -> List[QuestionnaireItem]:
        """Generate structured QuestionnaireItem list for a scheme in the target language.

        Args:
            scheme_id: Unique scheme identifier (e.g. 'PM_KISAN').
            language: Target language code ('en', 'te', 'hi'). Defaults to 'en'.

        Returns:
            List[QuestionnaireItem]: Ordered, localized question list.

        Raises:
            NotFoundError: If scheme does not exist in the repository.
        """
        scheme = scheme_repository.get_by_id(scheme_id)
        if not scheme:
            raise NotFoundError(f"Scheme with ID '{scheme_id}' was not found.")

        normalized_id = scheme.scheme_id.upper()
        raw_specs = self.SCHEME_SPECS.get(normalized_id, [])

        # Fallback to English if requested language is unsupported
        lang = language.lower() if language and language.lower() in self.SUPPORTED_LANGUAGES else "en"

        items: List[QuestionnaireItem] = []
        for spec in raw_specs:
            trans = spec["translations"].get(lang) or spec["translations"].get("en", {})
            label = trans.get("label", spec["id"])
            help_text = trans.get("help_text")
            options = trans.get("options") or spec.get("options")

            item = QuestionnaireItem(
                id=spec["id"],
                label=label,
                type=spec["type"],
                options=options,
                help_text=help_text,
                required=spec["required"],
                criterion_id=spec["criterion_id"],
                validation_rule=spec.get("validation_rule"),
                order=spec["order"],
                category=spec.get("category"),
            )
            items.append(item)

        # Sort strictly by order
        items.sort(key=lambda x: x.order)
        return items

    def get_question_by_id(
        self, scheme_id: str, question_id: str, language: str = "en"
    ) -> Optional[QuestionnaireItem]:
        """Retrieve an individual localized QuestionnaireItem by its ID."""
        questionnaire = self.get_questionnaire(scheme_id, language=language)
        for q in questionnaire:
            if q.id == question_id:
                return q
        return None

    def get_all_scheme_questionnaires(
        self, language: str = "en"
    ) -> Dict[str, List[QuestionnaireItem]]:
        """Retrieve questionnaires for all available verified schemes."""
        schemes = scheme_repository.get_all()
        result: Dict[str, List[QuestionnaireItem]] = {}
        for s in schemes:
            result[s.scheme_id] = self.get_questionnaire(s.scheme_id, language=language)
        return result

    def get_criterion_mapping(self, scheme_id: str) -> Dict[str, Dict[str, Any]]:
        """Return the mapping metadata linking criterion IDs to official conditions."""
        normalized_id = scheme_id.upper()
        specs = self.SCHEME_SPECS.get(normalized_id, [])
        return {
            spec["criterion_id"]: {
                "question_id": spec["id"],
                "type": spec["type"],
                "required": spec["required"],
                "order": spec["order"],
                "category": spec["category"],
                "condition_type": spec["condition_type"],
                "scheme_condition": spec["scheme_condition"],
            }
            for spec in specs
        }

    def get_unmapped_criteria(self, scheme_id: str) -> List[Dict[str, str]]:
        """Return statutory conditions not directly queried, along with justifications."""
        normalized_id = scheme_id.upper()
        return self.UNMAPPED_CRITERIA_REGISTRY.get(normalized_id, [])

    def get_required_criterion_ids(self, scheme_id: str) -> List[str]:
        """Return list of criterion IDs that are mandatory for eligibility evaluation."""
        questions = self.get_questionnaire(scheme_id)
        return [q.id for q in questions if q.required]

    def to_pending_questions(self, items: List[QuestionnaireItem]) -> List[PendingQuestion]:
        """Convert a list of QuestionnaireItems into PendingQuestions for API responses."""
        return [item.to_pending_question() for item in items]

    def to_eligibility_questions(
        self, items: List[QuestionnaireItem]
    ) -> List[EligibilityQuestion]:
        """Convert a list of QuestionnaireItems into base EligibilityQuestions."""
        return [item.to_eligibility_question() for item in items]


# Default service instance
questionnaire_mapping_service = QuestionnaireMappingService()

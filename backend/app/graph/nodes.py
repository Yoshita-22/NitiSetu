import logging
from typing import Any, Dict, List
from langgraph.types import interrupt
from app.graph.state import NitiSetuState
from app.repositories.scheme_repository import scheme_repository
from app.services.document_service import document_service
from app.services.eligibility_service import eligibility_service
from app.services.intent_classifier_service import intent_classifier_service
from app.services.nyaykosh_service import nyaykosh_service
from app.services.response_aggregator_service import ResponseAggregatorService
from app.services.scheme_service import scheme_service

logger = logging.getLogger("nitsetu.graph_nodes")


async def classify_intent_node(state: NitiSetuState) -> Dict[str, Any]:
    """Classifies user intent and extracts civic entities using Groq or fallback."""
    query = state.get("user_query", "")
    doc_id = state.get("document_id")

    classification = await intent_classifier_service.classify_query(query, document_id=doc_id)

    return {
        "intent": classification.intent.value,
        "secondary_intents": [i.value for i in classification.secondary_intents],
        "language": classification.detected_language,
        "extracted_entities": classification.extracted_entities.model_dump(),
        "classification_source": classification.source,
        "task_status": {"classify_intent": "COMPLETED"},
    }


async def law_retrieval_node(state: NitiSetuState) -> Dict[str, Any]:
    """Retrieves legal statutes and citizen rights via NyayKosh."""
    entities = state.get("extracted_entities", {})
    query = (
        entities.get("law_name")
        or entities.get("legal_topic")
        or entities.get("section_number")
        or state.get("user_query", "")
    )

    try:
        response = await nyaykosh_service.search_laws(query)
        raw_items = [item.model_dump() for item in response.results]
        return {
            "law_results": raw_items,
            "task_status": {"law_retrieval": "COMPLETED"},
        }
    except Exception as e:
        logger.error(f"Law retrieval node failed: {e}")
        return {
            "errors": [{"service": "law_retrieval", "error": str(e)}],
            "task_status": {"law_retrieval": "FAILED"},
        }


def scheme_retrieval_node(state: NitiSetuState) -> Dict[str, Any]:
    """Retrieves government scheme details and benefits from verified dataset."""
    entities = state.get("extracted_entities", {})
    scheme_id = entities.get("scheme_id")
    scheme_name = entities.get("scheme_name")
    query = scheme_name or state.get("user_query", "")

    try:
        found_schemes = []
        if scheme_id:
            scheme = scheme_repository.get_by_id(scheme_id)
            if scheme:
                found_schemes.append(scheme)

        if not found_schemes and query:
            found_schemes = scheme_repository.search(query)

        if not found_schemes:
            # Default to all schemes if none matched explicitly
            found_schemes = scheme_repository.get_all()[:2]

        return {
            "scheme_results": [s.model_dump() for s in found_schemes],
            "task_status": {"scheme_retrieval": "COMPLETED"},
        }
    except Exception as e:
        logger.error(f"Scheme retrieval node failed: {e}")
        return {
            "errors": [{"service": "scheme_retrieval", "error": str(e)}],
            "task_status": {"scheme_retrieval": "FAILED"},
        }


def document_retrieval_node(state: NitiSetuState) -> Dict[str, Any]:
    """Retrieves uploaded document metadata and extracted text pages."""
    entities = state.get("extracted_entities", {})
    doc_id = entities.get("document_id") or state.get("document_id")

    try:
        if not doc_id:
            # Check if any documents exist in repository
            all_docs = document_service.list_documents()
            if all_docs:
                doc_id = all_docs[-1].document_id
            else:
                return {
                    "document_results": [],
                    "errors": [{"service": "document_retrieval", "error": "No uploaded document found in active session."}],
                    "task_status": {"document_retrieval": "FAILED"},
                }

        pages_resp = document_service.get_document_pages(doc_id)
        return {
            "document_results": [pages_resp.model_dump()],
            "task_status": {"document_retrieval": "COMPLETED"},
        }
    except Exception as e:
        logger.error(f"Document retrieval node failed: {e}")
        return {
            "errors": [{"service": "document_retrieval", "error": str(e)}],
            "task_status": {"document_retrieval": "FAILED"},
        }


def eligibility_workflow_node(state: NitiSetuState) -> Dict[str, Any]:
    """Sequential eligibility workflow with human-in-the-loop interruption."""
    entities = state.get("extracted_entities", {})
    scheme_id = entities.get("scheme_id")

    # 1. Resolve target scheme
    scheme = None
    if scheme_id:
        scheme = scheme_repository.get_by_id(scheme_id)

    if not scheme:
        search_term = entities.get("scheme_name") or state.get("user_query", "")
        matches = scheme_repository.search(search_term)
        scheme = matches[0] if matches else scheme_repository.get_by_id("PM_KISAN")

    scheme_id = scheme.scheme_id

    # 2. Retrieve scheme questionnaire
    q_resp = eligibility_service.get_questions_for_scheme(scheme_id)

    # 3. Consolidate currently available answers
    current_answers = dict(state.get("applicant_details", {}))
    if entities.get("applicant_info"):
        current_answers.update(entities["applicant_info"])

    # 4. Check for missing required questions
    missing = [q for q in q_resp.questions if q.required and q.id not in current_answers]

    if missing:
        pending_questions_payload = [
            {
                "field": q.id,
                "question": q.label,
                "input_type": q.type,
                "options": q.options,
                "help_text": q.help_text,
            }
            for q in missing
        ]

        logger.info(
            f"Eligibility info incomplete for {scheme_id}. Pausing workflow with LangGraph interrupt() for {len(missing)} question(s)."
        )

        # Trigger human-in-the-loop pause. Checkpoint is persisted by LangGraph.
        resumed_answers = interrupt({
            "type": "eligibility_questions",
            "scheme_id": scheme.scheme_id,
            "scheme_name": scheme.scheme_name,
            "questions": pending_questions_payload,
            "message": f"To assess your eligibility for {scheme.scheme_name}, please provide the following details:",
        })

        if isinstance(resumed_answers, dict):
            current_answers.update(resumed_answers)

    # 5. Evaluate eligibility deterministically
    eval_response = eligibility_service.evaluate_eligibility(scheme_id, current_answers)

    return {
        "scheme_results": [scheme.model_dump()],
        "eligibility_results": eval_response.model_dump(),
        "applicant_details": current_answers,
        "task_status": {"eligibility_workflow": "COMPLETED"},
    }


def general_response_node(state: NitiSetuState) -> Dict[str, Any]:
    """Node for conversational greetings and general assistant guidance."""
    return {
        "task_status": {"general_response": "COMPLETED"},
    }


def unsupported_query_node(state: NitiSetuState) -> Dict[str, Any]:
    """Node for handling out-of-scope queries politely."""
    return {
        "task_status": {"unsupported_query": "COMPLETED"},
    }


def response_aggregator_node(state: NitiSetuState) -> Dict[str, Any]:
    """Aggregates all branch outputs, synthesizes natural language, and formats citations."""
    aggregated = ResponseAggregatorService.aggregate(state)
    return {
        "final_response": aggregated["final_response"],
        "response_metadata": aggregated["response_metadata"],
        "workflow_status": "COMPLETED",
        "task_status": {"response_aggregator": "COMPLETED"},
    }

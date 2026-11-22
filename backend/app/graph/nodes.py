import logging
from typing import Any, Dict, List
from langgraph.types import interrupt
from app.graph.state import NitiSetuState
from app.repositories.scheme_repository import scheme_repository
from app.services.answer_collection_service import answer_collection_service
from app.services.document_service import document_service
from app.services.eligibility_service import eligibility_service
from app.services.intent_classifier_service import intent_classifier_service
from app.services.nyaykosh_service import nyaykosh_service
from app.services.questionnaire_mapping_service import questionnaire_mapping_service
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


async def document_retrieval_node(state: NitiSetuState) -> Dict[str, Any]:
    """Retrieves uploaded document context and synthesizes grounded answers using RAG."""
    entities = state.get("extracted_entities", {})
    doc_id = entities.get("document_id") or state.get("document_id")
    user_id = state.get("user_id") or "anonymous_citizen"
    query = state.get("user_query", "")
    language = state.get("language", "en")

    try:
        if not doc_id:
            # Check if any documents exist in repository for user or session
            user_docs = document_service.list_documents(owner_id=user_id)
            if not user_docs:
                user_docs = document_service.list_documents()

            if user_docs:
                doc_id = user_docs[-1].document_id
            else:
                return {
                    "document_results": [],
                    "errors": [{"service": "document_retrieval", "error": "No uploaded document found in active session."}],
                    "task_status": {"document_retrieval": "FAILED"},
                }

        # Perform semantic vector retrieval & grounded QA
        qa_response = await document_service.query_document(
            query=query,
            user_id=user_id,
            document_id=doc_id,
            language=language,
        )

        return {
            "document_results": [qa_response.model_dump()],
            "task_status": {"document_retrieval": "COMPLETED"},
        }
    except Exception as e:
        logger.error(f"Document retrieval node failed: {e}")
        return {
            "errors": [{"service": "document_retrieval", "error": str(e)}],
            "task_status": {"document_retrieval": "FAILED"},
        }


async def eligibility_workflow_node(state: NitiSetuState) -> Dict[str, Any]:
    """Sequential eligibility workflow with multi-turn collection and human-in-the-loop interruption."""
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
    conversation_id = state.get("conversation_id", "default_thread")
    language = state.get("language", "en")
    user_id = state.get("user_id", "anonymous_citizen")

    # 2. Get or initialize active AssessmentState in AnswerCollectionService
    assessment = answer_collection_service.get_assessment(conversation_id)
    if not assessment or assessment.scheme_id != scheme_id:
        assessment = answer_collection_service.start_assessment(
            conversation_id=conversation_id,
            scheme_id=scheme_id,
            language=language,
            user_id=user_id,
        )

    # 3. Synchronize any upfront applicant details or entities
    initial_details = dict(state.get("applicant_details", {}))
    if entities.get("applicant_info"):
        initial_details.update(entities["applicant_info"])

    if initial_details:
        answer_collection_service.submit_direct_answers(
            conversation_id=conversation_id,
            answers=initial_details,
            language=language,
        )
        assessment = answer_collection_service.get_assessment(conversation_id)

    # 4. If assessment is brand new (turn_count == 0) and user_query has potential criteria, extract answers from it
    if assessment.turn_count == 0 and state.get("user_query"):
        await answer_collection_service.process_user_message(
            conversation_id=conversation_id,
            message=state["user_query"],
            language=language,
        )
        assessment = answer_collection_service.get_assessment(conversation_id)

    # 5. Multi-turn collection loop with LangGraph interrupt()
    all_questions = questionnaire_mapping_service.get_questionnaire(scheme_id, language=assessment.language)
    required_ids = [q.id for q in all_questions if q.required]

    while not assessment.is_ready_for_evaluation(required_ids):
        next_q = answer_collection_service.get_next_question(assessment)
        unanswered_items = [q for q in all_questions if q.id in assessment.unanswered_question_ids]
        if not unanswered_items and next_q:
            unanswered_items = [next_q]

        if assessment.clarification_required and next_q:
            rule_hint = next_q.validation_rule.clarification_hint if next_q.validation_rule else None
            ans_prompt = assessment.answers.get(next_q.id).clarification_prompt if next_q.id in assessment.answers else None
            prompt_msg = rule_hint or ans_prompt or f"Could you please clarify: {next_q.label}?"
        elif next_q:
            prompt_msg = f"To assess your eligibility for {scheme.scheme_name}: {next_q.label}"
            if next_q.help_text:
                prompt_msg += f" ({next_q.help_text})"
        else:
            prompt_msg = f"To assess your eligibility for {scheme.scheme_name}, please provide the following details:"

        interrupt_payload = {
            "type": "eligibility_questions",
            "scheme_id": scheme.scheme_id,
            "scheme_name": scheme.scheme_name,
            "current_question": next_q.to_pending_question().model_dump() if next_q else None,
            "questions": [q.to_pending_question().model_dump() for q in unanswered_items],
            "message": prompt_msg,
            "clarification_required": assessment.clarification_required,
            "validation_errors": list(assessment.validation_errors),
            "turn_count": assessment.turn_count,
        }

        logger.info(
            f"Eligibility info incomplete for {scheme_id} in {conversation_id}. "
            f"Pausing workflow via interrupt() for question '{next_q.id if next_q else 'pending'}'."
        )

        resumed_input = interrupt(interrupt_payload)
        if resumed_input is None:
            break

        # Process user answer(s) from resume
        if isinstance(resumed_input, dict):
            if "message" in resumed_input and len(resumed_input) == 1:
                await answer_collection_service.process_user_message(
                    conversation_id=conversation_id,
                    message=resumed_input["message"],
                    language=assessment.language,
                )
            elif "answers" in resumed_input and isinstance(resumed_input["answers"], dict):
                answer_collection_service.submit_direct_answers(
                    conversation_id=conversation_id,
                    answers=resumed_input["answers"],
                    language=assessment.language,
                )
            else:
                answer_collection_service.submit_direct_answers(
                    conversation_id=conversation_id,
                    answers=resumed_input,
                    language=assessment.language,
                )
        elif isinstance(resumed_input, str):
            await answer_collection_service.process_user_message(
                conversation_id=conversation_id,
                message=resumed_input,
                language=assessment.language,
            )

        assessment = answer_collection_service.get_assessment(conversation_id)

    # 6. Evaluation handoff
    clean_data = assessment.get_clean_applicant_data()
    eval_response = eligibility_service.evaluate_eligibility(scheme_id, clean_data)

    assessment.collection_status = "COMPLETED"
    answer_collection_service.save_assessment(assessment)

    return {
        "scheme_results": [scheme.model_dump()],
        "eligibility_results": eval_response.model_dump(),
        "applicant_details": clean_data,
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

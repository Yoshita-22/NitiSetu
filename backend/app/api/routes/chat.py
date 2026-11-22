import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from langgraph.types import Command
from app.graph.workflow import compiled_nitsetu_workflow
from app.repositories.conversation_repository import conversation_repository
from app.schemas.chat import ChatTestRequest, ChatTestResponse
from app.schemas.chat_query_schema import (
    ChatQueryRequest,
    ChatQueryResponse,
    ChatResumeRequest,
    ExecutionStatus,
    PendingQuestion,
)

logger = logging.getLogger("nitsetu.chat_routes")

router = APIRouter()


# ============================================================================
# Phase 0 Integration Verification Endpoint (Preserved for compatibility)
# ============================================================================
@router.post(
    "/test",
    response_model=ChatTestResponse,
    summary="Phase 0 Test Chat Verification Endpoint",
    description="Development verification endpoint for testing frontend-to-backend integration.",
)
def chat_test(payload: ChatTestRequest) -> ChatTestResponse:
    """Echo the received message with a development confirmation message."""
    return ChatTestResponse(
        success=True,
        message="This is a development response from PolicyPilot backend.",
        received_message=payload.message,
    )


# ============================================================================
# Phase 2 Intelligent LangGraph Orchestration Endpoints
# ============================================================================
@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Submit query to LangGraph intelligent orchestration engine",
    description=(
        "Processes citizen query through intent classification, conditional routing, "
        "parallel domain retrieval (Law, Scheme, Document), and sequential eligibility. "
        "Supports human-in-the-loop interruption if applicant details are missing."
    ),
)
async def process_chat_query(payload: ChatQueryRequest) -> ChatQueryResponse:
    """Executes the NitiSetu LangGraph workflow for a new user turn."""
    logger.info(f"Received query for conversation {payload.conversation_id}: '{payload.message}'")

    # 1. Persist user turn
    conversation_repository.save_message(
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
        metadata={"document_id": payload.document_id},
        user_id=payload.user_id or "anonymous_citizen",
    )

    # 2. Prepare initial graph state
    initial_state = {
        "user_query": payload.message,
        "conversation_id": payload.conversation_id,
        "document_id": payload.document_id,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": payload.conversation_id}}

    try:
        # 3. Asynchronously invoke LangGraph compiled workflow
        result = await compiled_nitsetu_workflow.ainvoke(initial_state, config=config)

        # 4. Handle human-in-the-loop interruption (e.g. eligibility questionnaire)
        interrupts = result.get("__interrupt__")
        if interrupts:
            interrupt_item = interrupts[0]
            interrupt_val = interrupt_item.value if hasattr(interrupt_item, "value") else interrupt_item
            questions_raw = interrupt_val.get("questions", []) if isinstance(interrupt_val, dict) else []
            pending_questions = [PendingQuestion(**q) for q in questions_raw]
            prompt_msg = (
                interrupt_val.get("message", "Please answer the following questions to check your eligibility:")
                if isinstance(interrupt_val, dict)
                else "Please provide more details:"
            )

            # Persist assistant interrupt prompt
            conversation_repository.save_message(
                conversation_id=payload.conversation_id,
                role="assistant",
                content=prompt_msg,
                metadata={"status": "waiting_for_user", "pending_questions": [q.model_dump() for q in pending_questions]},
                user_id=payload.user_id or "anonymous_citizen",
            )

            return ChatQueryResponse(
                status="waiting_for_user",
                conversation_id=payload.conversation_id,
                language=result.get("language", "en"),
                intent=result.get("intent", "SCHEME_ELIGIBILITY"),
                answer=prompt_msg,
                results={"scheme_results": result.get("scheme_results", [])},
                sources=[],
                execution=ExecutionStatus(
                    completed_tasks=list(result.get("task_status", {}).keys()),
                    failed_tasks=[],
                    partial_failure=False,
                ),
                pending_questions=pending_questions,
            )

        # 5. Normal completion: aggregate structured results & citations
        final_answer = result.get("final_response", "Unable to complete request.")
        response_meta = result.get("response_metadata", {})
        sources = response_meta.get("citations", [])
        task_status = result.get("task_status", {})
        completed = [k for k, v in task_status.items() if v == "COMPLETED"]
        failed = [k for k, v in task_status.items() if v == "FAILED"]
        partial_failure = response_meta.get("partial_failure", False)

        structured_results: Dict[str, Any] = {}
        if result.get("law_results"):
            structured_results["law_results"] = result["law_results"]
        if result.get("scheme_results"):
            structured_results["scheme_results"] = result["scheme_results"]
        if result.get("document_results"):
            structured_results["document_results"] = result["document_results"]
        if result.get("eligibility_results"):
            structured_results["eligibility_results"] = result["eligibility_results"]

        # Persist assistant completed response
        conversation_repository.save_message(
            conversation_id=payload.conversation_id,
            role="assistant",
            content=final_answer,
            metadata={"sources": sources, "intent": result.get("intent")},
            user_id=payload.user_id or "anonymous_citizen",
        )

        return ChatQueryResponse(
            status="completed",
            conversation_id=payload.conversation_id,
            language=result.get("language", "en"),
            intent=result.get("intent", "GENERAL_QUERY"),
            answer=final_answer,
            results=structured_results,
            sources=sources,
            execution=ExecutionStatus(
                completed_tasks=completed,
                failed_tasks=failed,
                partial_failure=partial_failure,
            ),
            pending_questions=[],
        )

    except Exception as e:
        logger.exception(f"Error processing query for {payload.conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution error: {str(e)}",
        )


@router.post(
    "/resume",
    response_model=ChatQueryResponse,
    summary="Resume interrupted LangGraph workflow with citizen answers",
    description="Supplies answers to human-in-the-loop pending questions and resumes workflow execution from checkpoint.",
)
async def resume_chat_query(payload: ChatResumeRequest) -> ChatQueryResponse:
    """Resumes paused workflow with user supplied answers via LangGraph Command(resume=...)."""
    logger.info(f"Resuming workflow for conversation {payload.conversation_id} with answers: {payload.answers}")

    # 1. Persist user response
    conversation_repository.save_message(
        conversation_id=payload.conversation_id,
        role="user",
        content="[Submitted required details]",
        metadata={"answers": payload.answers},
        user_id=payload.user_id or "anonymous_citizen",
    )

    config = {"configurable": {"thread_id": payload.conversation_id}}

    try:
        # 2. Resume execution using Command(resume=answers)
        result = await compiled_nitsetu_workflow.ainvoke(Command(resume=payload.answers), config=config)

        # 3. Check if subsequent interrupt occurred
        interrupts = result.get("__interrupt__")
        if interrupts:
            interrupt_item = interrupts[0]
            interrupt_val = interrupt_item.value if hasattr(interrupt_item, "value") else interrupt_item
            questions_raw = interrupt_val.get("questions", []) if isinstance(interrupt_val, dict) else []
            pending_questions = [PendingQuestion(**q) for q in questions_raw]
            prompt_msg = (
                interrupt_val.get("message", "Additional information needed:")
                if isinstance(interrupt_val, dict)
                else "Please provide more details:"
            )

            conversation_repository.save_message(
                conversation_id=payload.conversation_id,
                role="assistant",
                content=prompt_msg,
                metadata={"status": "waiting_for_user", "pending_questions": [q.model_dump() for q in pending_questions]},
                user_id=payload.user_id or "anonymous_citizen",
            )

            return ChatQueryResponse(
                status="waiting_for_user",
                conversation_id=payload.conversation_id,
                language=result.get("language", "en"),
                intent=result.get("intent", "SCHEME_ELIGIBILITY"),
                answer=prompt_msg,
                results={"scheme_results": result.get("scheme_results", [])},
                sources=[],
                execution=ExecutionStatus(
                    completed_tasks=list(result.get("task_status", {}).keys()),
                    failed_tasks=[],
                    partial_failure=False,
                ),
                pending_questions=pending_questions,
            )

        # 4. Completed execution after resume
        final_answer = result.get("final_response", "Eligibility evaluation complete.")
        response_meta = result.get("response_metadata", {})
        sources = response_meta.get("citations", [])
        task_status = result.get("task_status", {})
        completed = [k for k, v in task_status.items() if v == "COMPLETED"]
        failed = [k for k, v in task_status.items() if v == "FAILED"]
        partial_failure = response_meta.get("partial_failure", False)

        structured_results: Dict[str, Any] = {}
        if result.get("scheme_results"):
            structured_results["scheme_results"] = result["scheme_results"]
        if result.get("eligibility_results"):
            structured_results["eligibility_results"] = result["eligibility_results"]
        if result.get("law_results"):
            structured_results["law_results"] = result["law_results"]
        if result.get("document_results"):
            structured_results["document_results"] = result["document_results"]

        conversation_repository.save_message(
            conversation_id=payload.conversation_id,
            role="assistant",
            content=final_answer,
            metadata={"sources": sources, "intent": result.get("intent")},
            user_id=payload.user_id or "anonymous_citizen",
        )

        return ChatQueryResponse(
            status="completed",
            conversation_id=payload.conversation_id,
            language=result.get("language", "en"),
            intent=result.get("intent", "SCHEME_ELIGIBILITY"),
            answer=final_answer,
            results=structured_results,
            sources=sources,
            execution=ExecutionStatus(
                completed_tasks=completed,
                failed_tasks=failed,
                partial_failure=partial_failure,
            ),
            pending_questions=[],
        )

    except Exception as e:
        logger.exception(f"Error resuming workflow for {payload.conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph resume error: {str(e)}",
        )


@router.get(
    "/history/{conversation_id}",
    summary="Get conversation history turns",
    description="Retrieves the chronological message history for a specific conversation thread.",
)
def get_conversation_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Returns conversation history turns for a given thread."""
    return conversation_repository.get_conversation(conversation_id)


@router.get(
    "/conversations",
    summary="List active conversation threads",
    description="Lists summary metadata of active threads for a citizen.",
)
def list_conversations(user_id: str = "anonymous_citizen") -> List[Dict[str, Any]]:
    """Lists summary metadata of active threads for a citizen."""
    return conversation_repository.list_conversations(user_id)

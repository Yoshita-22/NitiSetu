from fastapi import APIRouter
from app.schemas.chat import ChatTestRequest, ChatTestResponse

router = APIRouter()


@router.post(
    "/test",
    response_model=ChatTestResponse,
    summary="Phase 0 Test Chat Verification Endpoint",
    description=(
        "Development verification endpoint for testing frontend-to-backend integration. "
        "NOTICE: This is an isolated Phase 0 stub. It does not invoke LLMs, RAG, "
        "or live government scheme databases."
    ),
)
def chat_test(payload: ChatTestRequest) -> ChatTestResponse:
    """Echo the received message with a development confirmation message."""
    return ChatTestResponse(
        success=True,
        message="This is a development response from PolicyPilot backend.",
        received_message=payload.message,
    )

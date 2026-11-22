import operator
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


def merge_dict_reducer(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Safe reducer to merge dictionaries updated by concurrent graph branches."""
    merged = dict(a or {})
    if b:
        merged.update(b)
    return merged


def overwrite_dict_reducer(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reducer that replaces or updates dictionary state."""
    if b is not None:
        return b
    return a or {}


class NitiSetuState(TypedDict):
    """Unified LangGraph state schema for NitiSetu civic query orchestration.

    Uses explicit reducers (operator.add and merge_dict_reducer) to support
    concurrent, non-destructive parallel branch execution.
    """

    # Session & Query Context
    conversation_id: str
    user_query: str
    user_id: str
    document_id: Optional[str]

    # Intent Classification & Entities
    intent: str
    secondary_intents: List[str]
    language: str
    extracted_entities: Dict[str, Any]
    classification_source: str

    # Domain Execution Outputs (with reducers for concurrent safety)
    document_results: Annotated[List[Dict[str, Any]], operator.add]
    law_results: Annotated[List[Dict[str, Any]], operator.add]
    scheme_results: Annotated[List[Dict[str, Any]], operator.add]
    eligibility_results: Annotated[Dict[str, Any], overwrite_dict_reducer]

    # Workflow Orchestration Tracking
    execution_plan: List[str]
    task_status: Annotated[Dict[str, str], merge_dict_reducer]
    errors: Annotated[List[Dict[str, Any]], operator.add]

    # Human-in-the-Loop & Sequential Assessment
    pending_questions: List[Dict[str, Any]]
    applicant_details: Annotated[Dict[str, Any], merge_dict_reducer]
    clarification_required: bool
    workflow_status: str  # "RUNNING", "WAITING_FOR_USER", "COMPLETED", "FAILED"

    # Aggregated Output
    final_response: str
    response_metadata: Dict[str, Any]

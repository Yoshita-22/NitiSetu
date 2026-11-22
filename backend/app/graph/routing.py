from typing import List, Union
from app.graph.state import NitiSetuState
from app.schemas.intent_schema import IntentType


def route_query_intent(state: NitiSetuState) -> Union[str, List[str]]:
    """Determines which graph branch(es) to invoke based on classified intent.

    Supports returning a list of node names to trigger genuine parallel branch execution.
    """
    intent = state.get("intent", IntentType.GENERAL_QUERY.value)
    secondary = state.get("secondary_intents", [])

    # 1. Multi-Intent Parallel Branches
    if intent == IntentType.MULTI_INTENT.value:
        parallel_nodes: List[str] = []

        # Document + Law parallel retrieval
        if (
            IntentType.DOCUMENT_QUERY.value in secondary
            and IntentType.LAW_INFORMATION.value in secondary
        ):
            return ["document_retrieval_node", "law_retrieval_node"]

        # Scheme + Law parallel retrieval
        if (
            IntentType.SCHEME_INFORMATION.value in secondary
            and IntentType.LAW_INFORMATION.value in secondary
        ):
            return ["scheme_retrieval_node", "law_retrieval_node"]

        # Scheme info + Scheme eligibility
        if (
            IntentType.SCHEME_INFORMATION.value in secondary
            and IntentType.SCHEME_ELIGIBILITY.value in secondary
        ):
            return "eligibility_workflow_node"

        # Default multi-intent handling: inspect secondary intents
        if IntentType.DOCUMENT_QUERY.value in secondary:
            parallel_nodes.append("document_retrieval_node")
        if IntentType.LAW_INFORMATION.value in secondary:
            parallel_nodes.append("law_retrieval_node")
        if IntentType.SCHEME_INFORMATION.value in secondary and IntentType.SCHEME_ELIGIBILITY.value not in secondary:
            parallel_nodes.append("scheme_retrieval_node")
        if IntentType.SCHEME_ELIGIBILITY.value in secondary:
            parallel_nodes.append("eligibility_workflow_node")

        if len(parallel_nodes) >= 2:
            return parallel_nodes
        elif len(parallel_nodes) == 1:
            return parallel_nodes[0]
        else:
            return ["scheme_retrieval_node", "law_retrieval_node"]

    # 2. Single Intent Direct Routes
    if intent == IntentType.LAW_INFORMATION.value:
        return "law_retrieval_node"

    if intent == IntentType.SCHEME_INFORMATION.value:
        return "scheme_retrieval_node"

    if intent == IntentType.SCHEME_ELIGIBILITY.value:
        return "eligibility_workflow_node"

    if intent == IntentType.DOCUMENT_QUERY.value:
        return "document_retrieval_node"

    if intent == IntentType.UNSUPPORTED_QUERY.value:
        return "unsupported_query_node"

    return "general_response_node"

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from app.graph.checkpointer import get_checkpointer
from app.graph.nodes import (
    classify_intent_node,
    document_retrieval_node,
    eligibility_workflow_node,
    general_response_node,
    law_retrieval_node,
    response_aggregator_node,
    scheme_retrieval_node,
    unsupported_query_node,
)
from app.graph.routing import route_query_intent
from app.graph.state import NitiSetuState


def build_nitsetu_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> StateGraph:
    """Builds and compiles the central NitiSetu LangGraph workflow.

    Supports:
    - Groq intent classification
    - Conditional routing
    - Concurrent parallel branches for multi-intent queries
    - Sequential eligibility evaluation
    - Human-in-the-loop interruption via interrupt()
    - Multi-source response aggregation and citations
    """
    workflow = StateGraph(NitiSetuState)

    # 1. Register Graph Nodes
    workflow.add_node("classify_intent_node", classify_intent_node)
    workflow.add_node("law_retrieval_node", law_retrieval_node)
    workflow.add_node("scheme_retrieval_node", scheme_retrieval_node)
    workflow.add_node("eligibility_workflow_node", eligibility_workflow_node)
    workflow.add_node("document_retrieval_node", document_retrieval_node)
    workflow.add_node("general_response_node", general_response_node)
    workflow.add_node("unsupported_query_node", unsupported_query_node)
    workflow.add_node("response_aggregator_node", response_aggregator_node)

    # 2. Add Start Edge
    workflow.add_edge(START, "classify_intent_node")

    # 3. Add Conditional Routing Edge
    workflow.add_conditional_edges(
        "classify_intent_node",
        route_query_intent,
        {
            "law_retrieval_node": "law_retrieval_node",
            "scheme_retrieval_node": "scheme_retrieval_node",
            "eligibility_workflow_node": "eligibility_workflow_node",
            "document_retrieval_node": "document_retrieval_node",
            "general_response_node": "general_response_node",
            "unsupported_query_node": "unsupported_query_node",
        },
    )

    # 4. Synchronize all branches into the Aggregation Node
    workflow.add_edge("law_retrieval_node", "response_aggregator_node")
    workflow.add_edge("scheme_retrieval_node", "response_aggregator_node")
    workflow.add_edge("eligibility_workflow_node", "response_aggregator_node")
    workflow.add_edge("document_retrieval_node", "response_aggregator_node")
    workflow.add_edge("general_response_node", "response_aggregator_node")
    workflow.add_edge("unsupported_query_node", "response_aggregator_node")

    # 5. Add End Edge
    workflow.add_edge("response_aggregator_node", END)

    active_checkpointer = checkpointer if checkpointer is not None else get_checkpointer()
    return workflow.compile(checkpointer=active_checkpointer)


# Default compiled workflow instance
compiled_nitsetu_workflow = build_nitsetu_graph()

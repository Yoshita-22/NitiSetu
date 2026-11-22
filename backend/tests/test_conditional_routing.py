import pytest
from app.graph.routing import route_query_intent
from app.schemas.intent_schema import IntentType


def test_route_law_information():
    state = {"intent": IntentType.LAW_INFORMATION.value, "secondary_intents": []}
    assert route_query_intent(state) == "law_retrieval_node"


def test_route_scheme_information():
    state = {"intent": IntentType.SCHEME_INFORMATION.value, "secondary_intents": []}
    assert route_query_intent(state) == "scheme_retrieval_node"


def test_route_scheme_eligibility():
    state = {"intent": IntentType.SCHEME_ELIGIBILITY.value, "secondary_intents": []}
    assert route_query_intent(state) == "eligibility_workflow_node"


def test_route_document_query():
    state = {"intent": IntentType.DOCUMENT_QUERY.value, "secondary_intents": []}
    assert route_query_intent(state) == "document_retrieval_node"


def test_route_unsupported_query():
    state = {"intent": IntentType.UNSUPPORTED_QUERY.value, "secondary_intents": []}
    assert route_query_intent(state) == "unsupported_query_node"


def test_route_general_query():
    state = {"intent": IntentType.GENERAL_QUERY.value, "secondary_intents": []}
    assert route_query_intent(state) == "general_response_node"


def test_route_multi_intent_parallel_law_scheme():
    state = {
        "intent": IntentType.MULTI_INTENT.value,
        "secondary_intents": [IntentType.SCHEME_INFORMATION.value, IntentType.LAW_INFORMATION.value],
    }
    routed = route_query_intent(state)
    assert isinstance(routed, list)
    assert "scheme_retrieval_node" in routed
    assert "law_retrieval_node" in routed


def test_route_multi_intent_parallel_law_document():
    state = {
        "intent": IntentType.MULTI_INTENT.value,
        "secondary_intents": [IntentType.DOCUMENT_QUERY.value, IntentType.LAW_INFORMATION.value],
    }
    routed = route_query_intent(state)
    assert isinstance(routed, list)
    assert "document_retrieval_node" in routed
    assert "law_retrieval_node" in routed

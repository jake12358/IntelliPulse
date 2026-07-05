import logging

from app.agents.state import AgentState
from app.core.logger import log_timing
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


def retriever_node(state: AgentState) -> AgentState:
    with log_timing(logger, "agent.retriever"):
        query = state.get("query", "")
        if "document_ids" in state and not state.get("document_ids"):
            return {**state, "retrieved_docs": []}
        docs = search_service.search(query, top_k=8, document_ids=state.get("document_ids"))
        return {**state, "retrieved_docs": docs}

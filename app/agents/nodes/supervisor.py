import logging

from app.agents.state import AgentState
from app.core.logger import log_timing

logger = logging.getLogger(__name__)


def supervisor_node(state: AgentState) -> AgentState:
    with log_timing(logger, "agent.supervisor"):
        if not state.get("retrieved_docs"):
            next_step = "retriever"
        elif not state.get("comparison_matrix"):
            next_step = "comparator"
        elif not state.get("sentiment_scores"):
            next_step = "sentiment"
        elif not state.get("final_report"):
            next_step = "reporter"
        else:
            next_step = "end"
        logger.info("Supervisor route decision: %s", next_step)
        return {**state, "next_step": next_step}

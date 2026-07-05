import logging

from app.agents.state import AgentState
from app.core.logger import log_timing

logger = logging.getLogger(__name__)


POSITIVE = {"好", "优秀", "稳定", "高效", "领先", "推荐", "便捷"}
NEGATIVE = {"差", "慢", "贵", "复杂", "故障", "投诉", "不好"}


def sentiment_node(state: AgentState) -> AgentState:
    with log_timing(logger, "agent.sentiment"):
        scores = {}
        for company in state.get("companies", []):
            text = "\n".join(
                doc.get("content", "")
                for doc in state.get("retrieved_docs", [])
                if doc.get("company") == company
            )
            positive = sum(text.count(word) for word in POSITIVE)
            negative = sum(text.count(word) for word in NEGATIVE)
            label = "neutral"
            if positive > negative:
                label = "positive"
            elif negative > positive:
                label = "negative"
            scores[company] = {"label": label, "positive": positive, "negative": negative}
        return {**state, "sentiment_scores": scores}

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, str]]
    query: str
    companies: list[str]
    document_ids: list[str]
    retrieved_docs: list[dict[str, Any]]
    comparison_matrix: dict[str, Any]
    sentiment_scores: dict[str, Any]
    final_report: str
    next_step: str

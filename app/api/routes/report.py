from fastapi import APIRouter, Query

from app.agents.graph import run_graph
from app.services.reporting_service import build_company_radars_with_llm, build_radar, source_preview

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{session_id}")
async def get_report(
    session_id: str,
    query: str = Query("对比本次提交的竞品资料"),
    document_ids: str = Query(""),
):
    scoped_document_ids = [item.strip() for item in document_ids.split(",") if item.strip()]
    state = run_graph(
        {
            "query": query,
            "document_ids": scoped_document_ids,
            "messages": [],
        }
    )
    sources = source_preview(state.get("retrieved_docs", []))
    return {
        "session_id": session_id,
        "report": state.get("final_report", ""),
        "radar": build_radar(state.get("comparison_matrix", {}), state.get("sentiment_scores", {})),
        "company_radars": build_company_radars_with_llm(
            state.get("comparison_matrix", {}),
            state.get("sentiment_scores", {}),
            sources,
        ),
        "matrix": state.get("comparison_matrix", {}),
        "sentiment": state.get("sentiment_scores", {}),
        "sources": sources,
    }

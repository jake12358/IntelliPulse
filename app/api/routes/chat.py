import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.agents.graph import stream_graph
from app.services.reporting_service import build_company_radars_with_llm, build_radar, source_preview

router = APIRouter(prefix="/chat", tags=["chat"])


def sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


@router.get("/stream")
async def chat_stream(
    query: str = Query(...),
    companies: str = Query(""),
    document_ids: str = Query(""),
):
    company_list = [item.strip() for item in companies.split(",") if item.strip()]
    scoped_document_ids = [item.strip() for item in document_ids.split(",") if item.strip()]

    async def generator():
        yield sse("start", {"message": "analysis started"})
        async for item in stream_graph(
            {
                "query": query,
                "companies": company_list,
                "document_ids": scoped_document_ids,
                "messages": [],
            }
        ):
            state = item["state"]
            sources = source_preview(state.get("retrieved_docs", []))
            yield sse(
                item["event"],
                {
                    "next_step": state.get("next_step"),
                    "report": state.get("final_report"),
                    "matrix": state.get("comparison_matrix", {}),
                    "sentiment": state.get("sentiment_scores", {}),
                    "radar": build_radar(
                        state.get("comparison_matrix", {}),
                        state.get("sentiment_scores", {}),
                    ),
                    "company_radars": build_company_radars_with_llm(
                        state.get("comparison_matrix", {}),
                        state.get("sentiment_scores", {}),
                        sources,
                    ),
                    "sources": sources,
                },
            )
        yield sse("done", {"message": "analysis finished"})

    return StreamingResponse(generator(), media_type="text/event-stream")

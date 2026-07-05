from fastapi import APIRouter

from app.core.config import get_settings
from app.db.redis_client import redis_vector_client
from app.db.repository import postgres_status

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/storage")
async def storage_status():
    settings = get_settings()
    redis_chunks = redis_vector_client._load_chunks_from_redis()
    postgres = await postgres_status()
    return {
        "redis": {
            "url": settings.redis_url,
            "available": redis_vector_client._redis is not None,
            "chunk_count": len(redis_chunks),
        },
        "postgres": {
            "url": settings.database_url,
            "available": postgres["available"],
            "counts": {"documents": postgres["documents"], "chunks": postgres["chunks"]},
            "error": postgres["error"],
        },
    }

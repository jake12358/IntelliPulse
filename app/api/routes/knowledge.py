from fastapi import APIRouter

from app.core.config import get_settings
from app.db.repository import postgres_counts
from app.db.redis_client import redis_vector_client
from app.services.document_registry import document_registry

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
async def list_documents():
    settings = get_settings()
    uploads = [
        {
            "filename": item.name,
            "size": item.stat().st_size,
            "path": str(item.relative_to(settings.base_dir)),
        }
        for item in settings.upload_path.glob("*")
        if item.is_file() and item.name != ".gitkeep"
    ]
    parsed = [
        {
            "filename": item.name,
            "size": item.stat().st_size,
            "path": str(item.relative_to(settings.base_dir)),
        }
        for item in settings.parsed_path.glob("*")
        if item.is_file() and item.name != ".gitkeep"
    ]
    chunks = redis_vector_client._load_chunks_from_redis()
    return {
        "documents": uploads,
        "parsed": parsed,
        "registry": document_registry.list_documents(),
        "postgres": await postgres_counts(),
        "chunks": chunks[:200],
        "chunk_count": len(chunks),
    }


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    settings = get_settings()
    target = settings.upload_path / filename
    if target.exists() and target.is_file():
        target.unlink()
        return {"deleted": True}
    return {"deleted": False}

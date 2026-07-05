import logging
from typing import Any

try:
    from sqlalchemy import func, select

    from app.db.postgres import AsyncSessionLocal, init_db
    from app.models.schemas import Chunk, Document
except Exception as import_exc:
    func = select = AsyncSessionLocal = init_db = Chunk = Document = None
    POSTGRES_IMPORT_ERROR = import_exc
else:
    POSTGRES_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


async def upsert_document_with_chunks(metadata: dict[str, Any], chunks: list[dict[str, Any]]) -> None:
    if POSTGRES_IMPORT_ERROR is not None:
        logger.warning("Postgres import failed: %s", POSTGRES_IMPORT_ERROR)
        return
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            document = await session.get(Document, metadata["document_id"])
            if document is None:
                document = Document(
                    id=metadata["document_id"],
                    filename=metadata.get("stored_filename", ""),
                    source_filename=metadata.get("source_filename", ""),
                    stored_filename=metadata.get("stored_filename", ""),
                    content_hash=metadata.get("content_hash", ""),
                    company=metadata.get("company", "未知竞品"),
                    category=metadata.get("category", "资料"),
                    path=metadata.get("stored_path", ""),
                    parsed_path=metadata.get("parsed_path", ""),
                    chunk_count=int(metadata.get("chunk_count", 0) or 0),
                    status=metadata.get("status", "processed"),
                )
                session.add(document)
            else:
                document.company = metadata.get("company", document.company)
                document.category = metadata.get("category", document.category)
                document.parsed_path = metadata.get("parsed_path", document.parsed_path)
                document.chunk_count = int(metadata.get("chunk_count", document.chunk_count) or 0)
                document.status = metadata.get("status", document.status)

            for chunk in chunks:
                existing = await session.get(Chunk, chunk["id"])
                if existing is not None:
                    continue
                session.add(
                    Chunk(
                        id=chunk["id"],
                        document_id=chunk["document_id"],
                        company=chunk.get("company", metadata.get("company", "未知竞品")),
                        category=chunk.get("category", metadata.get("category", "资料")),
                        source_filename=chunk.get("source_filename", metadata.get("source_filename", "")),
                        stored_path=chunk.get("stored_path", metadata.get("stored_path", "")),
                        parsed_path=chunk.get("parsed_path", metadata.get("parsed_path", "")),
                        content=chunk.get("content", ""),
                        position=int(chunk.get("position", 0) or 0),
                        token_count=int(chunk.get("token_count", 0) or 0),
                    )
                )
            await session.commit()
    except Exception as exc:
        logger.warning("Postgres upsert failed: %s", exc)


async def postgres_counts() -> dict[str, int]:
    if POSTGRES_IMPORT_ERROR is not None:
        logger.warning("Postgres import failed: %s", POSTGRES_IMPORT_ERROR)
        return {"documents": 0, "chunks": 0}
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            documents = await session.scalar(select(func.count(Document.id)))
            chunks = await session.scalar(select(func.count(Chunk.id)))
            return {"documents": int(documents or 0), "chunks": int(chunks or 0)}
    except Exception as exc:
        logger.warning("Postgres counts failed: %s", exc)
        return {"documents": 0, "chunks": 0}


async def postgres_status() -> dict[str, Any]:
    if POSTGRES_IMPORT_ERROR is not None:
        return {"available": False, "documents": 0, "chunks": 0, "error": str(POSTGRES_IMPORT_ERROR)}
    try:
        await init_db()
        async with AsyncSessionLocal() as session:
            documents = await session.scalar(select(func.count(Document.id)))
            chunks = await session.scalar(select(func.count(Chunk.id)))
            return {
                "available": True,
                "documents": int(documents or 0),
                "chunks": int(chunks or 0),
                "error": "",
            }
    except Exception as exc:
        logger.warning("Postgres status failed: %s", exc)
        return {"available": False, "documents": 0, "chunks": 0, "error": str(exc)}

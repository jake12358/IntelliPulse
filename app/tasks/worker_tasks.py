from pathlib import Path

from app.db.redis_client import redis_vector_client
from app.services.embedding_service import embedding_service
from app.services.parsing_service import parse_document
from app.tasks.celery_app import celery_app


def process_document(
    file_path: str,
    company: str,
    category: str = "general",
    original_filename: str | None = None,
    document_id: str | None = None,
    content_hash: str = "",
) -> dict:
    chunks = parse_document(
        Path(file_path),
        company=company,
        category=category,
        original_filename=original_filename,
        document_id=document_id,
        content_hash=content_hash,
    )
    embeddings = embedding_service.embed_documents(chunk["content"] for chunk in chunks)
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    inserted = redis_vector_client.insert_chunks(chunks)
    return {
        "inserted": inserted,
        "chunks": chunks,
        "document_id": chunks[0]["document_id"] if chunks else document_id,
        "content_hash": content_hash,
    }


@celery_app.task(name="process_document_task")
def process_document_task(
    file_path: str,
    company: str,
    category: str = "general",
    original_filename: str | None = None,
    document_id: str | None = None,
    content_hash: str = "",
) -> dict:
    result = process_document(file_path, company, category, original_filename, document_id, content_hash)
    return {**result, "category": category}

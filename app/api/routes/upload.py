from pathlib import Path
import os
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import get_settings
from app.db.repository import upsert_document_with_chunks
from app.db.redis_client import redis_vector_client
from app.services.document_classifier import classify_document
from app.services.document_registry import document_registry, sha256_bytes
from app.services.parsing_service import extract_text
from app.tasks.worker_tasks import process_document, process_document_task

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    company: str = Form(""),
    category: str = Form(""),
):
    settings = get_settings()
    suffix = Path(file.filename or "document.txt").suffix or ".txt"
    filename = f"{uuid4().hex}{suffix}"
    target = settings.upload_path / filename
    content = await file.read()
    original_filename = file.filename or "document.txt"
    content_hash = sha256_bytes(content)
    existing = document_registry.find_by_hash(content_hash)
    if existing:
        rebuilt = False
        redis_chunk_count = redis_vector_client.count_chunks_for_document(existing["document_id"])
        stored_path = existing.get("stored_path", "")
        if redis_chunk_count == 0 and stored_path:
            existing_file = settings.base_dir / stored_path
            if existing_file.exists():
                result = process_document(
                    str(existing_file),
                    existing.get("company", "未知竞品"),
                    existing.get("category", "资料"),
                    existing.get("source_filename", original_filename),
                    existing["document_id"],
                    content_hash,
                )
                metadata = {
                    **existing,
                    "chunk_count": result["inserted"],
                    "parsed_path": result["chunks"][0].get("parsed_path", "") if result["chunks"] else existing.get("parsed_path", ""),
                }
                document_registry.upsert(metadata)
                await upsert_document_with_chunks({**metadata, "status": "processed"}, result["chunks"])
                redis_chunk_count = result["inserted"]
                rebuilt = True
        return {
            "task_id": f"duplicate-{existing['document_id']}",
            "status": "duplicate",
            "filename": existing.get("stored_filename", ""),
            "original_filename": existing.get("source_filename", original_filename),
            "stored_path": stored_path,
            "document_id": existing["document_id"],
            "content_hash": content_hash,
            "company": existing.get("company", ""),
            "category": existing.get("category", ""),
            "classification": existing.get("classification", {}),
            "chunk_count": redis_chunk_count,
            "rebuilt": rebuilt,
            "message": "相同内容的文档已存在，本次未重复保存。",
        }

    document_id = uuid4().hex
    target.write_bytes(content)
    extracted_text = extract_text(target)
    classification = classify_document(extracted_text, original_filename)
    resolved_company = company.strip() or classification["company"]
    resolved_category = category.strip() or classification["category"]

    if os.getenv("INTELLIPULSE_TASK_MODE", "").lower() == "local":
        result = process_document(
            str(target),
            resolved_company,
            resolved_category,
            original_filename,
            document_id,
            content_hash,
        )
        document_registry.upsert(
            metadata := {
                "document_id": document_id,
                "content_hash": content_hash,
                "company": resolved_company,
                "category": resolved_category,
                "classification": classification,
                "source_filename": original_filename,
                "stored_filename": filename,
                "stored_path": str(target.relative_to(settings.base_dir)),
                "parsed_path": result["chunks"][0].get("parsed_path", "") if result["chunks"] else "",
                "chunk_count": result["inserted"],
            }
        )
        await upsert_document_with_chunks({**metadata, "status": "processed"}, result["chunks"])
        return {
            "task_id": f"local-{uuid4().hex}",
            "status": "finished",
            "filename": filename,
            "original_filename": original_filename,
            "stored_path": str(target.relative_to(settings.base_dir)),
            "document_id": document_id,
            "content_hash": content_hash,
            "company": resolved_company,
            "category": resolved_category,
            "classification": classification,
            "result": result,
        }

    try:
        task = process_document_task.delay(
            str(target),
            resolved_company,
            resolved_category,
            original_filename,
            document_id,
            content_hash,
        )
        document_registry.upsert(
            metadata := {
                "document_id": document_id,
                "content_hash": content_hash,
                "company": resolved_company,
                "category": resolved_category,
                "classification": classification,
                "source_filename": original_filename,
                "stored_filename": filename,
                "stored_path": str(target.relative_to(settings.base_dir)),
                "parsed_path": "",
                "chunk_count": 0,
            }
        )
        await upsert_document_with_chunks({**metadata, "status": "queued"}, [])
        return {
            "task_id": task.id,
            "status": "queued",
            "filename": filename,
            "original_filename": original_filename,
            "stored_path": str(target.relative_to(settings.base_dir)),
            "document_id": document_id,
            "content_hash": content_hash,
            "company": resolved_company,
            "category": resolved_category,
            "classification": classification,
        }
    except Exception:
        result = process_document(
            str(target),
            resolved_company,
            resolved_category,
            original_filename,
            document_id,
            content_hash,
        )
        document_registry.upsert(
            metadata := {
                "document_id": document_id,
                "content_hash": content_hash,
                "company": resolved_company,
                "category": resolved_category,
                "classification": classification,
                "source_filename": original_filename,
                "stored_filename": filename,
                "stored_path": str(target.relative_to(settings.base_dir)),
                "parsed_path": result["chunks"][0].get("parsed_path", "") if result["chunks"] else "",
                "chunk_count": result["inserted"],
            }
        )
        await upsert_document_with_chunks({**metadata, "status": "processed"}, result["chunks"])
        return {
            "task_id": f"local-{uuid4().hex}",
            "status": "finished",
            "filename": filename,
            "original_filename": original_filename,
            "stored_path": str(target.relative_to(settings.base_dir)),
            "document_id": document_id,
            "content_hash": content_hash,
            "company": resolved_company,
            "category": resolved_category,
            "classification": classification,
            "result": result,
        }

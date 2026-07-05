from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".csv", ".html", ".htm"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""

    if suffix in {".docx", ".doc"}:
        try:
            from docx import Document

            doc = Document(str(file_path))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception:
            return ""

    try:
        from unstructured.partition.auto import partition

        return "\n".join(str(element) for element in partition(filename=str(file_path)))
    except Exception:
        return file_path.read_text(encoding="utf-8", errors="ignore")


def split_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= max_chars:
            current = f"{current}\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        current = paragraph

    if current:
        chunks.append(current)

    normalized: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            normalized.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            normalized.append(chunk[start : start + max_chars])
            start += max_chars - overlap
    return normalized


def parse_document(
    file_path: Path,
    company: str,
    category: str = "general",
    original_filename: str | None = None,
    document_id: str | None = None,
    content_hash: str = "",
) -> list[dict]:
    text = extract_text(file_path)
    settings = get_settings()
    resolved_document_id = document_id or uuid4().hex
    parsed_file = settings.parsed_path / f"{file_path.stem}-{uuid4().hex}.txt"
    parsed_file.write_text(text, encoding="utf-8")

    chunks = split_text(text)
    return [
        {
            "id": f"{resolved_document_id}-{index}",
            "document_id": resolved_document_id,
            "content_hash": content_hash,
            "company": company,
            "category": category,
            "source_filename": original_filename or file_path.name,
            "stored_filename": file_path.name,
            "stored_path": str(file_path.relative_to(settings.base_dir)),
            "parsed_path": str(parsed_file.relative_to(settings.base_dir)),
            "content": chunk,
            "position": index,
            "token_count": max(1, len(chunk) // 2),
        }
        for index, chunk in enumerate(chunks)
    ]

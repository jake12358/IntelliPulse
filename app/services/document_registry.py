import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class DocumentRegistry:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.path = self.settings.base_dir / "data" / "documents.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"documents": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"documents": []}

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def find_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        for item in self._read().get("documents", []):
            if item.get("content_hash") == content_hash:
                return item
        return None

    def upsert(self, metadata: dict[str, Any]) -> dict[str, Any]:
        payload = self._read()
        documents = payload.setdefault("documents", [])
        for index, item in enumerate(documents):
            if item.get("document_id") == metadata.get("document_id"):
                documents[index] = {**item, **metadata}
                self._write(payload)
                return documents[index]
        documents.append(metadata)
        self._write(payload)
        return metadata

    def list_documents(self) -> list[dict[str, Any]]:
        return self._read().get("documents", [])


document_registry = DocumentRegistry()

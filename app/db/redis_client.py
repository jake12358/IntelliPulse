import json
import math
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    dot = sum(left[index] * right[index] for index in range(length))
    left_norm = math.sqrt(sum(value * value for value in left[:length])) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right[:length])) or 1.0
    return dot / (left_norm * right_norm)


@dataclass
class LocalVectorStore:
    chunks: list[dict[str, Any]] = field(default_factory=list)

    def insert(self, chunks: list[dict[str, Any]]) -> int:
        self.chunks.extend(chunks)
        return len(chunks)

    def search(self, vector: list[float], top_k: int = 20) -> list[dict[str, Any]]:
        scored = []
        for chunk in self.chunks:
            score = cosine_similarity(vector, chunk.get("embedding", []))
            scored.append({**chunk, "score": score})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    def fulltext(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        terms = [term.lower() for term in query.split() if term]
        scored = []
        for chunk in self.chunks:
            content = chunk.get("content", "").lower()
            score = sum(content.count(term) for term in terms)
            if score:
                scored.append({**chunk, "score": float(score)})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


local_vector_store = LocalVectorStore()


class RedisVectorClient:
    index_name = "idx:intellipulse:chunks"

    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis = None
        try:
            import redis

            self._redis = redis.from_url(self.settings.redis_url, decode_responses=True)
            self._redis.ping()
        except Exception:
            self._redis = None

    def ensure_index(self) -> None:
        if not self._redis:
            return
        try:
            from redis.commands.search.field import TagField, TextField, VectorField
            from redis.commands.search.indexDefinition import IndexDefinition, IndexType

            try:
                self._redis.ft(self.index_name).info()
                return
            except Exception:
                pass

            schema = (
                TextField("$.content", as_name="content"),
                TagField("$.company", as_name="company"),
                VectorField(
                    "$.embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": self.settings.local_embedding_dim,
                        "DISTANCE_METRIC": "COSINE",
                    },
                    as_name="embedding",
                ),
            )
            self._redis.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=["chunk:"], index_type=IndexType.JSON),
            )
        except Exception:
            return

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        local_vector_store.insert(chunks)
        if not self._redis:
            return len(chunks)

        self.ensure_index()
        for chunk in chunks:
            key = f"chunk:{chunk['id']}"
            payload = {
                "id": chunk["id"],
                "document_id": chunk.get("document_id", ""),
                "content_hash": chunk.get("content_hash", ""),
                "company": chunk.get("company", ""),
                "category": chunk.get("category", ""),
                "source_filename": chunk.get("source_filename", ""),
                "stored_filename": chunk.get("stored_filename", ""),
                "stored_path": chunk.get("stored_path", ""),
                "parsed_path": chunk.get("parsed_path", ""),
                "content": chunk.get("content", ""),
                "position": chunk.get("position", 0),
                "token_count": chunk.get("token_count", 0),
                "embedding": chunk.get("embedding", []),
            }
            try:
                self._redis.json().set(key, "$", payload)
            except Exception:
                self._redis.set(key, json.dumps(payload, ensure_ascii=False))
        return len(chunks)

    def _load_chunks_from_redis(self) -> list[dict[str, Any]]:
        if not self._redis:
            return []

        chunks: list[dict[str, Any]] = []
        try:
            for key in self._redis.scan_iter(match="chunk:*", count=200):
                payload = None
                try:
                    payload = self._redis.json().get(key)
                except Exception:
                    raw = self._redis.get(key)
                    if raw:
                        payload = json.loads(raw)
                if isinstance(payload, dict):
                    chunks.append(payload)
        except Exception:
            return []
        return chunks

    def _filter_documents(
        self,
        chunks: list[dict[str, Any]],
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not document_ids:
            return chunks
        allowed = set(document_ids)
        return [chunk for chunk in chunks if chunk.get("document_id") in allowed]

    def count_chunks_for_document(self, document_id: str) -> int:
        chunks = self._load_chunks_from_redis()
        if chunks:
            return sum(1 for chunk in chunks if chunk.get("document_id") == document_id)
        return sum(1 for chunk in local_vector_store.chunks if chunk.get("document_id") == document_id)

    def vector_search(
        self,
        vector: list[float],
        top_k: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        redis_chunks = self._load_chunks_from_redis()
        if redis_chunks:
            redis_chunks = self._filter_documents(redis_chunks, document_ids)
            scored = [
                {**chunk, "score": cosine_similarity(vector, chunk.get("embedding", []))}
                for chunk in redis_chunks
            ]
            return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
        chunks = local_vector_store.search(vector, top_k=1000)
        return self._filter_documents(chunks, document_ids)[:top_k]

    def fulltext_search(
        self,
        query: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        redis_chunks = self._load_chunks_from_redis()
        if redis_chunks:
            redis_chunks = self._filter_documents(redis_chunks, document_ids)
            terms = [term.lower() for term in query.split() if term]
            scored = []
            for chunk in redis_chunks:
                content = chunk.get("content", "").lower()
                score = sum(content.count(term) for term in terms)
                if score:
                    scored.append({**chunk, "score": float(score)})
            return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
        chunks = local_vector_store.fulltext(query, top_k=1000)
        return self._filter_documents(chunks, document_ids)[:top_k]


redis_vector_client = RedisVectorClient()

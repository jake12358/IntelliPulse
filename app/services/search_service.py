import hashlib
import json
from typing import Any

from app.db.redis_client import redis_vector_client
from app.services.embedding_service import embedding_service


class SearchService:
    def __init__(self) -> None:
        self.cache: dict[str, list[dict[str, Any]]] = {}

    def _cache_key(self, query: str, document_ids: list[str] | None = None) -> str:
        scope = ",".join(sorted(document_ids or []))
        return hashlib.sha256(f"{query.strip().lower()}::{scope}".encode("utf-8")).hexdigest()

    def vector_search(
        self,
        query: str,
        top_k: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        vector = embedding_service.embed_text(query)
        return redis_vector_client.vector_search(vector, top_k=top_k, document_ids=document_ids)

    def fulltext_search(
        self,
        query: str,
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return redis_vector_client.fulltext_search(query, top_k=top_k, document_ids=document_ids)

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        query_terms = set(query.lower().split())
        ranked = []
        seen = set()
        for candidate in candidates:
            content = candidate.get("content", "")
            key = candidate.get("id") or content[:80]
            if key in seen:
                continue
            seen.add(key)
            lexical = len(query_terms.intersection(set(content.lower().split())))
            score = float(candidate.get("score", 0.0)) + lexical * 0.15
            ranked.append({**candidate, "score": round(score, 4)})
        return sorted(ranked, key=lambda item: item["score"], reverse=True)[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        key = self._cache_key(query, document_ids)
        if key in self.cache:
            return json.loads(json.dumps(self.cache[key], ensure_ascii=False))

        candidates = self.vector_search(query, top_k=20, document_ids=document_ids)
        candidates += self.fulltext_search(query, top_k=10, document_ids=document_ids)
        results = self.rerank(query, candidates, top_k=top_k)
        self.cache[key] = results
        return results


search_service = SearchService()

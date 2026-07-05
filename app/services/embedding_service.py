import hashlib
import math
from typing import Iterable

from app.core.config import get_settings


def _stable_local_embedding(text: str, dim: int) -> list[float]:
    vector = [0.0] * dim
    tokens = [token for token in text.lower().replace("\n", " ").split(" ") if token]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dim = self.settings.local_embedding_dim

    def embed_text(self, text: str) -> list[float]:
        if self.settings.embedding_provider == "dashscope" and self.settings.dashscope_api_key:
            try:
                import dashscope

                dashscope.api_key = self.settings.dashscope_api_key
                response = dashscope.TextEmbedding.call(
                    model=self.settings.dashscope_embedding_model,
                    input=text,
                )
                return response.output["embeddings"][0]["embedding"]
            except Exception:
                pass
        return _stable_local_embedding(text, self.dim)

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


embedding_service = EmbeddingService()

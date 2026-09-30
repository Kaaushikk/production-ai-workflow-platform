import hashlib
import math
import re
from abc import ABC, abstractmethod

EMBEDDING_DIMENSION = 384
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(ABC):
    name: str
    dimension: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized vector for each input text."""


class HashEmbeddingProvider(EmbeddingProvider):
    """Offline lexical baseline used before a downloadable semantic model is added."""

    name = "hash-embedding-v1"
    dimension = EMBEDDING_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector


default_embedding_provider = HashEmbeddingProvider()


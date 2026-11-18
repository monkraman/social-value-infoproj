import socket

# Windows IPv6 blackhole mitigation: prioritize IPv4 addresses
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_first_getaddrinfo(*args, **kwargs):
    res = _orig_getaddrinfo(*args, **kwargs)
    ipv4 = [r for r in res if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else res
socket.getaddrinfo = _ipv4_first_getaddrinfo

import hashlib
import numpy as np
import httpx
from typing import List
from openai import OpenAI
from app.core.config import settings


class EmbeddingUnavailable(RuntimeError):
    """No real embedding could be produced (provider down, quota, or no key)."""


class EmbeddingService:
    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION
        self._openai_client = None

    @property
    def openai_client(self) -> OpenAI:
        if self._openai_client is None and settings.is_openai_configured:
            self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    def _generate_synthetic_vector(self, text: str) -> List[float]:
        """
        Generates a deterministic unit-normalized pseudo-embedding vector of 1536 dimensions.
        Used as an offline fallback when no API key is configured.
        """
        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self.dimension)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def _normalize_and_pad_vector(self, values: List[float]) -> List[float]:
        """Ensures the vector matches exactly the 1536 dimensions required by pgvector."""
        if len(values) == self.dimension:
            arr = np.array(values, dtype=np.float32)
        elif len(values) < self.dimension:
            arr = np.pad(values, (0, self.dimension - len(values)), mode='constant')
        else:
            arr = np.array(values[:self.dimension], dtype=np.float32)

        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def _fallback(self, texts: List[str], reason: str) -> List[List[float]]:
        """No real embedding: placeholder vectors only when explicitly allowed, otherwise an error.

        A placeholder vector is stored and searched exactly like a real one, so silently using it
        would make every search result look valid while being meaningless.
        """
        if settings.EMBEDDING_ALLOW_SYNTHETIC:
            print(f"[EmbeddingService] {reason} Using placeholder vectors (EMBEDDING_ALLOW_SYNTHETIC).")
            return [self._generate_synthetic_vector(t) for t in texts]
        raise EmbeddingUnavailable(reason)

    def get_embedding(self, text: str) -> List[float]:
        """Embedding from the active provider. Raises EmbeddingUnavailable when none can be made."""
        return self.get_embeddings([text])[0]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Embeddings for a batch of strings, from the active provider."""
        if not texts:
            return []
        cleaned = [" ".join(t.split()) or "empty" for t in texts]
        provider = settings.active_provider

        if provider == "openai" and settings.is_openai_configured:
            try:
                response = self.openai_client.embeddings.create(input=cleaned, model=settings.OPENAI_EMBEDDING_MODEL)
                return [self._normalize_and_pad_vector(item.embedding) for item in response.data]
            except Exception as e:
                return self._fallback(cleaned, f"OpenAI embedding failed: {e}")

        if provider == "gemini" and settings.is_gemini_configured:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_EMBEDDING_MODEL}:embedContent"
            out: List[List[float]] = []
            try:
                with httpx.Client(timeout=20.0) as client:
                    for text in cleaned:
                        r = client.post(url, params={"key": settings.GEMINI_API_KEY},
                                        json={"content": {"parts": [{"text": text}]}, "outputDimensionality": self.dimension})
                        if r.status_code != 200:
                            return self._fallback(cleaned, f"Gemini embedding failed (HTTP {r.status_code}).")
                        values = r.json().get("embedding", {}).get("values", [])
                        if not values:
                            return self._fallback(cleaned, "Gemini returned an empty embedding.")
                        out.append(self._normalize_and_pad_vector(values))
            except httpx.HTTPError as e:
                return self._fallback(cleaned, f"Gemini embedding failed: {e.__class__.__name__}.")
            return out

        return self._fallback(cleaned, "No AI provider is configured for embeddings.")


embedding_service = EmbeddingService()

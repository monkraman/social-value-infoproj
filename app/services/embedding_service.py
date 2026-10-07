import hashlib
import numpy as np
import httpx
from typing import List
from openai import OpenAI
from app.core.config import settings


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

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding using the active provider (Gemini, OpenAI, or Fallback)."""
        cleaned_text = text.replace("\n", " ").strip()
        if not cleaned_text:
            cleaned_text = "empty"

        provider = settings.active_provider

        # 1. Google Gemini Provider via Fast REST API
        if provider == "gemini" and settings.is_gemini_configured:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_EMBEDDING_MODEL}:embedContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "content": {"parts": [{"text": cleaned_text}]},
                    "outputDimensionality": self.dimension
                }
                with httpx.Client(timeout=15.0) as client:
                    r = client.post(url, json=payload)
                    if r.status_code == 200:
                        values = r.json().get("embedding", {}).get("values", [])
                        return self._normalize_and_pad_vector(values)
                    else:
                        print(f"[EmbeddingService] Gemini HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                print(f"[EmbeddingService] Gemini embedding error: {e}. Falling back to deterministic vector.")

        # 2. OpenAI Provider
        if provider == "openai" and settings.is_openai_configured:
            try:
                response = self.openai_client.embeddings.create(
                    input=[cleaned_text],
                    model=settings.OPENAI_EMBEDDING_MODEL
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"[EmbeddingService] OpenAI embedding error: {e}. Falling back to deterministic vector.")

        # 3. Offline / Fallback
        return self._generate_synthetic_vector(cleaned_text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of strings."""
        if not texts:
            return []

        provider = settings.active_provider
        cleaned_texts = [t.replace("\n", " ").strip() or "empty" for t in texts]

        # 1. OpenAI batch embedding
        if provider == "openai" and settings.is_openai_configured:
            try:
                response = self.openai_client.embeddings.create(
                    input=cleaned_texts,
                    model=settings.OPENAI_EMBEDDING_MODEL
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                print(f"[EmbeddingService] OpenAI batch embedding error: {e}. Falling back.")
                return [self._generate_synthetic_vector(t) for t in cleaned_texts]

        # 2. Gemini or Fallback
        return [self.get_embedding(t) for t in cleaned_texts]


embedding_service = EmbeddingService()

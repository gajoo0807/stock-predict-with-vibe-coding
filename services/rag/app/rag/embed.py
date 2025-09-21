from __future__ import annotations
from typing import List
import os
import numpy as np
from app.core.config import settings


class EmbeddingBackend:
    def __init__(self):
        self.backend = (settings.EMBEDDING_BACKEND or "auto").lower()
        self.local_model_name = settings.EMBEDDING_MODEL_LOCAL
        self._local_model = None

    def _ensure_local(self):
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._local_model = SentenceTransformer(self.local_model_name)
            except Exception:
                # As a last resort, create a trivial bag-of-words hashing embedder
                class _TinyEmbedder:
                    def __init__(self, dim: int = 384):
                        self.dim = dim
                    def encode(self, texts, normalize_embeddings=True):
                        import numpy as _np
                        vecs = []
                        for t in texts:
                            v = _np.zeros(self.dim, dtype=float)
                            for i, ch in enumerate(t[: self.dim * 4]):
                                v[i % self.dim] += (ord(ch) % 7) / 7.0
                            if normalize_embeddings:
                                n = _np.linalg.norm(v)
                                if n:
                                    v = v / n
                            vecs.append(v)
                        return _np.array(vecs)
                self._local_model = _TinyEmbedder()

    def _openai_available(self) -> bool:
        key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        return bool(key)

    def embed_chunks(self, chunk_texts: List[str]):
        if not chunk_texts:
            return np.zeros((0, 384), dtype=float)

        backend = self.backend
        if backend == "auto":
            backend = "openai" if self._openai_available() else "local"

        if backend == "openai" and self._openai_available():
            try:
                from openai import OpenAI  # type: ignore

                client = OpenAI(api_key=settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))
                model = "text-embedding-3-small"
                resp = client.embeddings.create(input=chunk_texts, model=model)
                data = [d.embedding for d in resp.data]
                arr = np.array(data, dtype=float)
                return arr
            except Exception:
                # fallback to local
                pass

        # local backend
        self._ensure_local()
        vecs = self._local_model.encode(chunk_texts, normalize_embeddings=True)
        return np.array(vecs, dtype=float)



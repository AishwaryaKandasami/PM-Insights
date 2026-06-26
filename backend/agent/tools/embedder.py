"""
Embedder Tool — Phase 3
Generates embeddings for atom texts using Google text-embedding-004.
"""
import logging
import time

import numpy as np
import google.generativeai as genai

from config.settings import GEMINI_API_KEY, EMBEDDING_MODEL, MIN_DELAY_SECONDS

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# Google Embedding API accepts up to 100 texts per batch
_BATCH_SIZE = 100


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Embed a list of texts using the configured embedding model.

    Args:
        texts: List of strings to embed.

    Returns:
        2D numpy array of shape (len(texts), embedding_dim).
    """
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    all_embeddings: list[list[float]] = []
    embed_dim: int | None = None

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        try:
            result = genai.embed_content(
                model=f"models/{EMBEDDING_MODEL}",
                content=batch,
                task_type="CLUSTERING",
            )
            batch_embeds = result["embedding"]
            all_embeddings.extend(batch_embeds)
            if embed_dim is None and batch_embeds:
                embed_dim = len(batch_embeds[0])
            logger.info(
                "Embedded batch %d–%d of %d texts",
                i, min(i + _BATCH_SIZE, len(texts)), len(texts),
            )
        except Exception as exc:
            logger.error("Embedding error on batch %d: %s", i, exc)
            # Fill failed batch with tiny epsilon (not zero) to avoid
            # cosine distance errors in sklearn
            dim = embed_dim or 3072
            all_embeddings.extend([[1e-10] * dim] * len(batch))
        finally:
            time.sleep(MIN_DELAY_SECONDS)

    return np.array(all_embeddings, dtype=np.float32)


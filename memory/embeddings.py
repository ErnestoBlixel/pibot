"""
Memoria semántica con embeddings para PiBot.
Almacena y busca documentos usando pgvector.
"""

import json
import httpx
import structlog

from config import settings

logger = structlog.get_logger()

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIM = 1536


async def get_embedding(text: str) -> list[float]:
    """Obtiene el embedding de un texto usando OpenRouter."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"][0]["embedding"]


async def store(text: str, source_type: str = "general", metadata: dict | None = None) -> None:
    """Almacena un documento con su embedding en pgvector."""
    from memory.postgres import _get_pool

    embedding = await get_embedding(text)
    pool = _get_pool()
    await pool.execute(
        "INSERT INTO memory_embeddings (content, embedding, source_type, metadata) "
        "VALUES ($1, $2::vector, $3, $4)",
        text, json.dumps(embedding), source_type, json.dumps(metadata or {}),
    )
    logger.info("embedding_stored", source_type=source_type, chars=len(text))


async def search(query: str, limit: int = 5, source_type: str | None = None) -> list[dict]:
    """Busca documentos similares por coseno."""
    from memory.postgres import _get_pool

    embedding = await get_embedding(query)
    pool = _get_pool()

    if source_type:
        rows = await pool.fetch(
            "SELECT content, source_type, metadata, "
            "1 - (embedding <=> $1::vector) AS similarity "
            "FROM memory_embeddings WHERE source_type = $2 "
            "ORDER BY embedding <=> $1::vector LIMIT $3",
            json.dumps(embedding), source_type, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT content, source_type, metadata, "
            "1 - (embedding <=> $1::vector) AS similarity "
            "FROM memory_embeddings "
            "ORDER BY embedding <=> $1::vector LIMIT $2",
            json.dumps(embedding), limit,
        )
    return [dict(r) for r in rows]

"""
Cliente Redis para PiBot.
Cache, confirmaciones pendientes y pub/sub.
"""

import redis.asyncio as aioredis
import structlog

from config import settings

logger = structlog.get_logger()

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Crea la conexión Redis al arrancar."""
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await _redis.ping()
    logger.info("redis_connected")


async def close_redis() -> None:
    """Cierra la conexión Redis al apagar."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("redis_closed")


def get_redis() -> aioredis.Redis:
    """Devuelve la instancia de Redis activa."""
    if _redis is None:
        raise RuntimeError("Redis no inicializado. Llama a init_redis() primero.")
    return _redis


async def cache_get(key: str) -> str | None:
    """Lee un valor de la cache."""
    r = get_redis()
    return await r.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    """Escribe un valor en la cache con TTL en segundos."""
    r = get_redis()
    await r.set(key, value, ex=ttl)


async def cache_delete(key: str) -> None:
    """Elimina una clave de la cache."""
    r = get_redis()
    await r.delete(key)

"""
Capa de persistencia PostgreSQL para PiBot.
Pool de conexiones con asyncpg. Funciones de historial y auditoría.
"""

import asyncpg
import structlog

from config import settings

logger = structlog.get_logger()

_pool: asyncpg.Pool | None = None


def _get_pool() -> asyncpg.Pool:
    """Devuelve el pool activo o lanza error si no se ha inicializado."""
    if _pool is None:
        raise RuntimeError("Pool de PostgreSQL no inicializado. Llama a init_pool() primero.")
    return _pool


def _clean_dsn(dsn: str) -> str:
    """Convierte postgresql+asyncpg:// a postgresql:// para asyncpg."""
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return dsn


async def init_pool() -> None:
    """Crea el pool de conexiones al arrancar."""
    global _pool
    dsn = _clean_dsn(settings.DATABASE_URL)
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    logger.info("postgres_pool_created")


async def close_pool() -> None:
    """Cierra el pool de conexiones al apagar."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("postgres_pool_closed")


# ---------------------------------------------------------------------------
# Historial de conversaciones
# ---------------------------------------------------------------------------

async def save_message(session_id: str, role: str, content: str, channel: str = "api", metadata: dict | None = None) -> None:
    """Guarda un mensaje en el historial de conversaciones."""
    import json as _json
    pool = _get_pool()
    await pool.execute(
        "INSERT INTO agent_conversations (session_id, role, content, channel, metadata) "
        "VALUES ($1, $2, $3, $4, $5::jsonb)",
        session_id, role, content, channel, _json.dumps(metadata or {}),
    )


async def get_history(session_id: str, limit: int = 20) -> list[dict]:
    """Devuelve los últimos mensajes de una sesión."""
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT role, content, channel, created_at FROM agent_conversations "
        "WHERE session_id = $1 ORDER BY created_at DESC LIMIT $2",
        session_id, limit,
    )
    return [dict(r) for r in reversed(rows)]


async def get_context_messages(session_id: str, limit: int = 10) -> list[dict]:
    """Devuelve mensajes recientes formateados como contexto para el LLM."""
    rows = await get_history(session_id, limit=limit)
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ---------------------------------------------------------------------------
# Auditoría de acciones
# ---------------------------------------------------------------------------

async def log_audit(
    agent_name: str,
    action: str,
    status: str = "ok",
    detail: str | None = None,
    session_id: str | None = None,
) -> None:
    """Registra una acción en la tabla de auditoría."""
    pool = _get_pool()
    await pool.execute(
        "INSERT INTO agent_audit_log (agent_name, action, status, error_message, user_id) "
        "VALUES ($1, $2, $3, $4, $5)",
        agent_name, action, status, detail, session_id,
    )


async def get_audit(
    limit: int = 50,
    agent_name: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Devuelve entradas de auditoría con filtros opcionales."""
    pool = _get_pool()
    conditions = []
    params: list = []
    idx = 1
    if agent_name:
        conditions.append(f"agent_name = ${idx}")
        params.append(agent_name)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = await pool.fetch(
        f"SELECT * FROM agent_audit_log {where} ORDER BY created_at DESC LIMIT ${idx}",
        *params,
    )
    return [dict(r) for r in rows]

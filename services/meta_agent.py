"""
Meta-agente de PiBot.
Gestiona la auto-mejora de prompts: propuestas, aprobaciones y rollbacks.
"""

import json
import structlog

from memory.postgres import _get_pool, log_audit
from orchestrator.llm import chat_completion

logger = structlog.get_logger()


async def propose_prompt_change(
    prompt_name: str,
    new_content: str,
    change_reason: str,
) -> int | None:
    """
    Propone un cambio de prompt. Se almacena como 'pending' hasta que sea aprobado.
    Retorna la versión propuesta o None si falla.
    """
    pool = _get_pool()

    # Obtener versión actual
    row = await pool.fetchrow(
        "SELECT COALESCE(MAX(version), 0) AS max_v FROM agent_prompt_versions WHERE prompt_name = $1",
        prompt_name,
    )
    next_version = row["max_v"] + 1

    await pool.execute(
        "INSERT INTO agent_prompt_versions (prompt_name, version, content, change_reason, status) "
        "VALUES ($1, $2, $3, $4, 'pending')",
        prompt_name, next_version, new_content, change_reason,
    )

    await log_audit("meta_agent", "propose_prompt", detail=f"{prompt_name} v{next_version}: {change_reason}")
    logger.info("prompt_proposed", prompt=prompt_name, version=next_version)
    return next_version


async def approve_prompt(prompt_name: str, version: int) -> bool:
    """Aprueba una propuesta de cambio de prompt."""
    pool = _get_pool()
    result = await pool.execute(
        "UPDATE agent_prompt_versions SET status = 'approved', approved_by = 'admin' "
        "WHERE prompt_name = $1 AND version = $2 AND status = 'pending'",
        prompt_name, version,
    )
    approved = result == "UPDATE 1"
    if approved:
        await log_audit("meta_agent", "approve_prompt", detail=f"{prompt_name} v{version}")
        logger.info("prompt_approved", prompt=prompt_name, version=version)
    return approved


async def reject_prompt(prompt_name: str, version: int) -> bool:
    """Rechaza una propuesta de cambio de prompt."""
    pool = _get_pool()
    result = await pool.execute(
        "UPDATE agent_prompt_versions SET status = 'rejected' "
        "WHERE prompt_name = $1 AND version = $2 AND status = 'pending'",
        prompt_name, version,
    )
    rejected = result == "UPDATE 1"
    if rejected:
        await log_audit("meta_agent", "reject_prompt", detail=f"{prompt_name} v{version}")
        logger.info("prompt_rejected", prompt=prompt_name, version=version)
    return rejected


async def get_active_prompt(prompt_name: str) -> str | None:
    """Devuelve el contenido del prompt aprobado más reciente."""
    pool = _get_pool()
    row = await pool.fetchrow(
        "SELECT content FROM agent_prompt_versions "
        "WHERE prompt_name = $1 AND status = 'approved' "
        "ORDER BY version DESC LIMIT 1",
        prompt_name,
    )
    return row["content"] if row else None


async def evaluate_prompt_performance(prompt_name: str) -> dict:
    """Evalúa el rendimiento de un prompt basándose en auditoría reciente."""
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT status, COUNT(*) as count FROM agent_audit "
        "WHERE agent_name = $1 AND created_at > NOW() - INTERVAL '7 days' "
        "GROUP BY status",
        prompt_name,
    )
    stats = {r["status"]: r["count"] for r in rows}
    total = sum(stats.values())
    success_rate = stats.get("ok", 0) / total if total > 0 else 0
    return {"prompt_name": prompt_name, "total": total, "stats": stats, "success_rate": success_rate}

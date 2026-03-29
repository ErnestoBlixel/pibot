"""
Servicio proactivo para PiBot.
Ejecuta tareas programadas y detecta patrones que requieren acción.
"""

import asyncio
import structlog

from memory.postgres import _get_pool, log_audit
from orchestrator.llm import chat_completion

logger = structlog.get_logger()


async def check_pending_tasks() -> list[dict]:
    """Revisa tareas pendientes que necesitan atención."""
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT * FROM agent_audit WHERE status = 'pending' "
        "AND created_at > NOW() - INTERVAL '24 hours' "
        "ORDER BY created_at DESC LIMIT 20"
    )
    return [dict(r) for r in rows]


async def analyze_patterns() -> str | None:
    """Analiza patrones recientes y sugiere mejoras si las hay."""
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT agent_name, action, status, COUNT(*) as count "
        "FROM agent_audit WHERE created_at > NOW() - INTERVAL '7 days' "
        "GROUP BY agent_name, action, status ORDER BY count DESC LIMIT 20"
    )
    if not rows:
        return None

    summary = "\n".join(
        f"- {r['agent_name']}/{r['action']}: {r['status']} x{r['count']}"
        for r in rows
    )

    prompt = [
        {"role": "system", "content": (
            "Analiza estos patrones de uso del sistema y sugiere mejoras concretas. "
            "Sé breve y práctico."
        )},
        {"role": "user", "content": f"Patrones de los últimos 7 días:\n{summary}"},
    ]
    return await chat_completion(prompt, temperature=0.5)


async def run_proactive_cycle() -> None:
    """Ejecuta un ciclo completo de tareas proactivas."""
    logger.info("proactive_cycle_start")
    try:
        # Verificar tareas pendientes
        pending = await check_pending_tasks()
        if pending:
            logger.info("proactive_pending_tasks", count=len(pending))

        # Análisis de patrones (solo si hay suficiente actividad)
        analysis = await analyze_patterns()
        if analysis:
            logger.info("proactive_analysis", summary=analysis[:200])
            await log_audit("proactive", "pattern_analysis", status="ok", detail=analysis[:500])

    except Exception as e:
        logger.error("proactive_cycle_error", error=str(e))
        await log_audit("proactive", "cycle", status="error", detail=str(e))

    logger.info("proactive_cycle_end")


async def start_proactive_loop(interval_minutes: int = 60) -> None:
    """Inicia el loop proactivo que se ejecuta periódicamente."""
    while True:
        await run_proactive_cycle()
        await asyncio.sleep(interval_minutes * 60)

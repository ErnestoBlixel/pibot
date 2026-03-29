"""
Utilidades de auditoría para PiBot.
Wrappers de conveniencia sobre memory.postgres.log_audit.
"""

import structlog

from memory.postgres import log_audit

logger = structlog.get_logger()


async def audit_action(
    agent_name: str,
    action: str,
    status: str = "ok",
    detail: str | None = None,
    session_id: str | None = None,
) -> None:
    """Registra una acción en auditoría con logging adicional."""
    logger.info(
        "audit",
        agent=agent_name,
        action=action,
        status=status,
        detail=detail[:200] if detail else None,
    )
    await log_audit(agent_name, action, status=status, detail=detail, session_id=session_id)

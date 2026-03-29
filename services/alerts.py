"""
Sistema de alertas para PiBot.
Crea y gestiona alertas que se notifican al equipo.
"""

import structlog

from memory.postgres import _get_pool

logger = structlog.get_logger()


async def create_alert(
    title: str,
    message: str,
    severity: str = "info",
    agent_name: str | None = None,
    session_id: str | None = None,
) -> int:
    """
    Crea una nueva alerta en la base de datos.
    severity: info, warning, error, critical
    Retorna el ID de la alerta.
    """
    pool = _get_pool()
    row = await pool.fetchrow(
        "INSERT INTO agent_alerts (title, message, severity, agent_name, session_id) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
        title, message, severity, agent_name, session_id,
    )
    alert_id = row["id"]
    logger.info("alert_created", id=alert_id, severity=severity, title=title[:80])

    # Notificar por Telegram si es crítica
    if severity in ("error", "critical"):
        try:
            from interfaces.telegram_bot import send_notification
            await send_notification(f"[{severity.upper()}] {title}\n{message[:500]}")
        except Exception as e:
            logger.error("alert_notification_failed", error=str(e))

    return alert_id


async def resolve_alert(alert_id: int) -> bool:
    """Marca una alerta como resuelta."""
    pool = _get_pool()
    result = await pool.execute(
        "UPDATE agent_alerts SET status = 'resolved', resolved_at = NOW() WHERE id = $1",
        alert_id,
    )
    resolved = result == "UPDATE 1"
    if resolved:
        logger.info("alert_resolved", id=alert_id)
    return resolved

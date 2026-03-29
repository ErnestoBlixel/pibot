"""
Heartbeat de PiBot.
Monitoreo de salud del sistema y notificaciones de estado.
"""

import asyncio
from datetime import datetime, timezone

import structlog

from memory.postgres import _get_pool, log_audit
from memory.redis_client import get_redis

logger = structlog.get_logger()


async def check_health() -> dict:
    """Verifica el estado de todos los servicios."""
    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "postgres": False,
        "redis": False,
    }

    # PostgreSQL
    try:
        pool = _get_pool()
        await pool.fetchval("SELECT 1")
        status["postgres"] = True
    except Exception as e:
        logger.error("health_postgres_fail", error=str(e))

    # Redis
    try:
        r = get_redis()
        await r.ping()
        status["redis"] = True
    except Exception as e:
        logger.error("health_redis_fail", error=str(e))

    status["healthy"] = all([status["postgres"], status["redis"]])
    return status


async def run_heartbeat(interval_seconds: int = 300) -> None:
    """Ejecuta el heartbeat periódicamente."""
    while True:
        try:
            health = await check_health()
            if health["healthy"]:
                logger.debug("heartbeat_ok")
            else:
                logger.warning("heartbeat_degraded", status=health)
                await log_audit("heartbeat", "health_check", status="warning",
                                detail=f"Servicios degradados: {health}")
                # Notificar si hay problemas
                try:
                    from interfaces.telegram_bot import send_notification
                    unhealthy = [k for k, v in health.items() if k not in ("timestamp", "healthy") and not v]
                    await send_notification(
                        f"⚠️ *Heartbeat*: Servicios degradados: {', '.join(unhealthy)}"
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error("heartbeat_error", error=str(e))

        await asyncio.sleep(interval_seconds)

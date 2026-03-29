"""
Sistema de confirmación de acciones sensibles para PiBot.
Usa Redis para almacenar confirmaciones pendientes.
"""

import json
import uuid
import structlog

from memory.redis_client import get_redis

logger = structlog.get_logger()

CONFIRMATION_TTL = 300  # 5 minutos


async def request_confirmation(action_description: str, session_id: str) -> bool:
    """
    Crea una solicitud de confirmación en Redis.
    Devuelve False inmediatamente — el usuario debe confirmar vía /confirm.
    """
    r = get_redis()
    key = f"confirm:{session_id}:{uuid.uuid4().hex[:8]}"
    payload = {
        "action": action_description,
        "session_id": session_id,
        "status": "pending",
    }
    await r.set(key, json.dumps(payload), ex=CONFIRMATION_TTL)
    logger.info("confirmation_requested", key=key, action=action_description[:80])
    # En el flujo real, se notifica al usuario y se espera respuesta
    # Por ahora, devolvemos False para indicar que falta confirmación
    return False


async def resolve_confirmation(redis_key: str, decision: str) -> str:
    """
    Resuelve una confirmación pendiente.
    decision: 'approve' o 'reject'
    """
    r = get_redis()
    raw = await r.get(redis_key)
    if not raw:
        return "expired_or_not_found"

    payload = json.loads(raw)
    if payload.get("status") != "pending":
        return "already_resolved"

    payload["status"] = decision
    await r.set(redis_key, json.dumps(payload), ex=60)
    logger.info("confirmation_resolved", key=redis_key, decision=decision)
    return decision

"""
Control de acceso por whitelist para PiBot.
Verifica que los usuarios de Telegram estén autorizados.
"""

import structlog

from config import settings

logger = structlog.get_logger()


def is_allowed(chat_id: str | int) -> bool:
    """Verifica si un chat_id está en la whitelist de Telegram."""
    allowed = settings.allowed_chat_ids
    result = str(chat_id) in allowed
    if not result:
        logger.warning("access_denied", chat_id=chat_id)
    return result

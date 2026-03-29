"""
Agente de WordPress para PiBot.
Gestión de contenido del blog: publicar, editar, listar posts.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class WordPressAgent(BaseAgent):
    name = "wordpress"
    description = "Gestión de contenido WordPress"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con WordPress."""
        logger.info("wordpress_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de WordPress requerida. "
                "Acciones posibles: list_posts, create_post, edit_post, publish_post, site_stats. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("wordpress_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de WordPress: {e}"

        action = intent.get("action", "unknown")
        await log_audit("wordpress", action, session_id=session_id)

        # Acciones destructivas requieren confirmación
        if action in ("publish_post", "edit_post"):
            confirmed = await self.confirm_action(
                f"WordPress: {action} — {message[:100]}", session_id
            )
            if not confirmed:
                return "Acción cancelada por el usuario."

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de WordPress de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de WordPress vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

"""
Agente de Google Calendar para PiBot.
Consulta, crea y gestiona eventos del calendario.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class CalendarAgent(BaseAgent):
    name = "calendar"
    description = "Gestión de Google Calendar"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con Google Calendar."""
        logger.info("calendar_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de Calendar requerida. "
                "Acciones posibles: list_events, create_event, update_event, delete_event, today_agenda. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("calendar_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de Calendar: {e}"

        action = intent.get("action", "unknown")
        await log_audit("calendar", action, session_id=session_id)

        # Acciones destructivas requieren confirmación
        if action in ("create_event", "update_event", "delete_event"):
            confirmed = await self.confirm_action(
                f"Calendar: {action} — {message[:100]}", session_id
            )
            if not confirmed:
                return "Acción cancelada por el usuario."

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de Calendar de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de Google Calendar vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

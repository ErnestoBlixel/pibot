"""
Agente de Gmail para PiBot.
Lee, busca y redacta correos electrónicos.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class GmailAgent(BaseAgent):
    name = "gmail"
    description = "Gestión de correos electrónicos vía Gmail"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con Gmail."""
        logger.info("gmail_handle", message=message[:80], session_id=session_id)

        # Analizar intención
        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de Gmail requerida. "
                "Acciones posibles: read_inbox, search_emails, compose_draft, summarize_emails. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("gmail_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de Gmail: {e}"

        action = intent.get("action", "unknown")
        await log_audit("gmail", action, session_id=session_id)

        # Por ahora, generar respuesta contextual
        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de Gmail de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de Gmail vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

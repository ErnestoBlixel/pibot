"""
Agente de Holded para PiBot.
Gestión de facturación, contactos y productos.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class HoldedAgent(BaseAgent):
    name = "holded"
    description = "Gestión de facturación y contabilidad con Holded"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con Holded."""
        logger.info("holded_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de Holded requerida. "
                "Acciones posibles: list_invoices, create_invoice, list_contacts, create_contact, "
                "list_products, financial_summary. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("holded_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de Holded: {e}"

        action = intent.get("action", "unknown")
        await log_audit("holded", action, session_id=session_id)

        # Acciones financieras requieren confirmación
        if action in ("create_invoice", "create_contact"):
            confirmed = await self.confirm_action(
                f"Holded: {action} — {message[:100]}", session_id
            )
            if not confirmed:
                return "Acción cancelada por el usuario."

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de Holded de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de Holded vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

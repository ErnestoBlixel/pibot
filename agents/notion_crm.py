"""
Agente de Notion CRM para PiBot.
Gestión de contactos comerciales y pipeline de ventas.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class NotionCRMAgent(BaseAgent):
    name = "notion_crm"
    description = "CRM y gestión de contactos comerciales en Notion"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con el CRM en Notion."""
        logger.info("notion_crm_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de CRM Notion requerida. "
                "Acciones posibles: list_leads, create_lead, update_lead, pipeline_summary, search_contacts. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("notion_crm_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de CRM Notion: {e}"

        action = intent.get("action", "unknown")
        await log_audit("notion_crm", action, session_id=session_id)

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de CRM Notion de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de Notion vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

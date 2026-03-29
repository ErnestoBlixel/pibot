"""
Agente de Notion Tasks para PiBot.
Gestión de tareas y proyectos en Notion.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class NotionTasksAgent(BaseAgent):
    name = "notion_tasks"
    description = "Gestión de tareas en Notion"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con tareas en Notion."""
        logger.info("notion_tasks_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de tareas Notion requerida. "
                "Acciones posibles: list_tasks, create_task, update_task, complete_task, task_summary. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("notion_tasks_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de tareas Notion: {e}"

        action = intent.get("action", "unknown")
        await log_audit("notion_tasks", action, session_id=session_id)

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de tareas Notion de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de Notion vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

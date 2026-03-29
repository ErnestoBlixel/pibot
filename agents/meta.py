"""
Meta-agente de PiBot.
Se encarga de la auto-mejora del sistema: optimización de prompts,
análisis de rendimiento y propuestas de cambios.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class MetaAgent(BaseAgent):
    name = "meta"
    description = "Auto-mejora del sistema y optimización de prompts"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes de meta-gestión del sistema."""
        logger.info("meta_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción meta requerida. "
                "Acciones posibles: analyze_performance, optimize_prompt, system_status, suggest_improvements. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("meta_intent_error", error=str(e))
            return f"No pude interpretar la solicitud meta: {e}"

        action = intent.get("action", "unknown")
        await log_audit("meta", action, session_id=session_id)

        response_prompt = [
            {"role": "system", "content": (
                "Eres el meta-agente de Pi. Tu trabajo es analizar y mejorar el propio sistema. "
                "Genera una respuesta útil sobre la acción solicitada. "
                "Si implica cambios en prompts, genera una propuesta detallada."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

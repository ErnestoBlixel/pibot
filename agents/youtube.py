"""
Agente de YouTube para PiBot.
Gestión de canal, métricas y contenido de video.
"""

import structlog

from agents.base import BaseAgent
from orchestrator.llm import chat_completion
from memory.postgres import log_audit

logger = structlog.get_logger()


class YouTubeAgent(BaseAgent):
    name = "youtube"
    description = "Gestión del canal de YouTube y métricas"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa solicitudes relacionadas con YouTube."""
        logger.info("youtube_handle", message=message[:80], session_id=session_id)

        intent_prompt = [
            {"role": "system", "content": (
                "Analiza el mensaje y determina la acción de YouTube requerida. "
                "Acciones posibles: channel_stats, video_analytics, search_videos, content_ideas. "
                "Responde SOLO con JSON: {\"action\": \"...\", \"params\": {...}}"
            )},
            {"role": "user", "content": message},
        ]
        try:
            intent_raw = await chat_completion(intent_prompt, temperature=0.1, json_mode=True)
            import json
            intent = json.loads(intent_raw)
        except Exception as e:
            logger.error("youtube_intent_error", error=str(e))
            return f"No pude interpretar la solicitud de YouTube: {e}"

        action = intent.get("action", "unknown")
        await log_audit("youtube", action, session_id=session_id)

        response_prompt = [
            {"role": "system", "content": (
                "Eres el agente de YouTube de Pi. Genera una respuesta útil sobre la acción solicitada. "
                "Si la acción requiere integración real, indica que la funcionalidad está pendiente de "
                "conectar con la API de YouTube vía n8n."
            )},
            {"role": "user", "content": f"Acción: {action}\nMensaje original: {message}"},
        ]
        return await chat_completion(response_prompt)

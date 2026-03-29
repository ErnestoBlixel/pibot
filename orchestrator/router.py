"""
Router inteligente de PiBot.
Clasifica mensajes y los dirige al agente adecuado.
"""

import json
import structlog

from orchestrator.llm import chat_completion
from orchestrator.prompts import ROUTER_PROMPT

logger = structlog.get_logger()

# Palabras clave como fallback rápido antes de llamar al LLM
KEYWORD_MAP = {
    "gmail": ["correo", "email", "mail", "mensaje de correo", "inbox", "bandeja"],
    "calendar": ["calendario", "evento", "reunión", "cita", "agenda", "meeting"],
    "youtube": ["youtube", "video", "vídeo", "canal", "suscriptores", "métricas youtube"],
    "wordpress": ["blog", "wordpress", "artículo", "post", "publicar", "wp"],
    "holded": ["factura", "holded", "presupuesto", "contacto holded", "producto holded"],
    "notion_tasks": ["tarea", "task", "pendiente", "to-do", "todo", "notion tarea"],
    "notion_crm": ["crm", "lead", "prospecto", "cliente potencial", "pipeline"],
}


def _keyword_match(text: str) -> str | None:
    """Intenta clasificar por palabras clave. Devuelve None si no hay match claro."""
    text_lower = text.lower()
    for agent, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return agent
    return None


async def route_message(text: str, session_id: str | None = None) -> dict:
    """
    Clasifica un mensaje y devuelve el agente sugerido.
    Retorna: {"agent": str, "confidence": float, "reason": str}
    """
    # Intento rápido por palabras clave
    kw_match = _keyword_match(text)
    if kw_match:
        logger.info("router_keyword_match", agent=kw_match, text=text[:80])
        return {"agent": kw_match, "confidence": 0.85, "reason": f"Keyword match: {kw_match}"}

    # Clasificación por LLM
    messages = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": text},
    ]
    try:
        raw = await chat_completion(messages, temperature=0.1, max_tokens=200, json_mode=True)
        result = json.loads(raw)
        logger.info("router_llm", agent=result.get("agent"), confidence=result.get("confidence"), text=text[:80])
        return result
    except Exception as e:
        logger.error("router_error", error=str(e))
        return {"agent": "general", "confidence": 0.5, "reason": f"Fallback por error: {e}"}

"""
Grafo de orquestación de PiBot.
Coordina el flujo completo: router → agente → respuesta.
"""

import structlog

from memory.postgres import save_message, get_context_messages, log_audit
from orchestrator.router import route_message
from orchestrator.llm import chat_completion
from orchestrator.prompts import SYSTEM_PROMPT

logger = structlog.get_logger()

# Registro de agentes disponibles
_AGENTS: dict = {}


def register_agent(name: str, handler):
    """Registra un agente en el grafo."""
    _AGENTS[name] = handler
    logger.info("agent_registered", name=name)


def _load_agents():
    """Carga todos los agentes disponibles (lazy)."""
    if _AGENTS:
        return
    from agents.gmail import GmailAgent
    from agents.youtube import YouTubeAgent
    from agents.meta import MetaAgent
    from agents.wordpress import WordPressAgent
    from agents.holded import HoldedAgent
    from agents.notion_tasks import NotionTasksAgent
    from agents.notion_crm import NotionCRMAgent
    from agents.calendar import CalendarAgent

    for cls in [GmailAgent, YouTubeAgent, MetaAgent, WordPressAgent,
                HoldedAgent, NotionTasksAgent, NotionCRMAgent, CalendarAgent]:
        agent = cls()
        register_agent(agent.name, agent)


async def process_message(message: str, session_id: str, channel: str = "api") -> dict:
    """
    Procesa un mensaje del usuario a través del grafo completo.
    Retorna: {"text": str, "agent_used": str | None, "voice_url": str | None}
    """
    _load_agents()

    # Guardar mensaje del usuario
    await save_message(session_id, "user", message, channel=channel)

    # 1. Intentar matchear un skill experto PRIMERO
    try:
        from skills.base import match_skill
        skill = match_skill(message)
        if skill:
            logger.info("skill_matched", skill=skill.name)
            context = await get_context_messages(session_id, limit=4)
            context_msgs = [{"role": r["role"], "content": r["content"]} for r in context]
            response_text = await skill.execute(message, context=context_msgs)
            await save_message(session_id, "assistant", response_text, channel=channel)
            await log_audit(f"skill:{skill.name}", "execute", status="ok", session_id=session_id)
            return {"text": response_text, "agent_used": f"skill:{skill.name}", "voice_url": None}
    except Exception as e:
        logger.warning("skill_match_error", error=str(e))

    # 2. Enrutar a agente n8n
    route = await route_message(message, session_id=session_id)
    agent_name = route["agent"]
    confidence = route.get("confidence", 0)

    logger.info("message_routed", agent=agent_name, confidence=confidence, session_id=session_id)

    # Ejecutar agente o responder con LLM general
    response_text: str
    if agent_name in _AGENTS and agent_name != "general":
        try:
            agent = _AGENTS[agent_name]
            response_text = await agent.handle(message, session_id=session_id, channel=channel)
            await log_audit(agent_name, "handle_message", status="ok", session_id=session_id)
        except Exception as e:
            logger.error("agent_error", agent=agent_name, error=str(e))
            await log_audit(agent_name, "handle_message", status="error", detail=str(e), session_id=session_id)
            response_text = f"Error al procesar con el agente {agent_name}: {e}"
    else:
        # Respuesta general con contexto
        context = await get_context_messages(session_id, limit=10)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + context + [{"role": "user", "content": message}]
        response_text = await chat_completion(messages)
        await log_audit("general", "chat", status="ok", session_id=session_id)

    # Guardar respuesta
    await save_message(session_id, "assistant", response_text, channel=channel)

    # TTS opcional
    voice_url = None
    if channel == "voice":
        try:
            from services.tts import synthesize
            voice_url = await synthesize(response_text)
        except Exception as e:
            logger.error("tts_error", error=str(e))

    return {"text": response_text, "agent_used": agent_name, "voice_url": voice_url}

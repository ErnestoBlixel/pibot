"""Agente de Holded — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class HoldedAgent(BaseAgent):
    name = "holded"
    description = "Gestión de Holded"
    webhook_path = "holded"

"""Agente de Meta — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class MetaAgent(BaseAgent):
    name = "meta"
    description = "Gestión de Meta (Facebook + Instagram)"
    webhook_path = "meta"

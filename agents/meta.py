"""Agente de meta — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class MetaAgent(BaseAgent):
    name = "meta"
    description = "Agente meta"
    webhook_path = "meta"

"""Agente de holded — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class HoldedAgent(BaseAgent):
    name = "holded"
    description = "Agente holded"
    webhook_path = "holded"

"""Agente de gmail — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class GmailAgent(BaseAgent):
    name = "gmail"
    description = "Agente gmail"
    webhook_path = "gmail"

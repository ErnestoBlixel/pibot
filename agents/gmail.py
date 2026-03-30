"""Agente de Gmail — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class GmailAgent(BaseAgent):
    name = "gmail"
    description = "Gestión de Gmail"
    webhook_path = "gmail"

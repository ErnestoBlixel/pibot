"""Agente de WordPress — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class WordPressAgent(BaseAgent):
    name = "wordpress"
    description = "Gestión de WordPress"
    webhook_path = "wordpress"

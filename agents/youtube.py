"""Agente de YouTube — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class YouTubeAgent(BaseAgent):
    name = "youtube"
    description = "Gestión de YouTube"
    webhook_path = "youtube"

"""Agente de youtube — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class YoutubeAgent(BaseAgent):
    name = "youtube"
    description = "Agente youtube"
    webhook_path = "youtube"

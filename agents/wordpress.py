"""Agente de wordpress — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class WordpressAgent(BaseAgent):
    name = "wordpress"
    description = "Agente wordpress"
    webhook_path = "wordpress"

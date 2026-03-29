"""Agente de notion_crm — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class Notion_crmAgent(BaseAgent):
    name = "notion_crm"
    description = "Agente notion_crm"
    webhook_path = "notion-crm"

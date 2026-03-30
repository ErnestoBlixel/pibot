"""Agente de Notion CRM — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class NotionCRMAgent(BaseAgent):
    name = "notion_crm"
    description = "Gestión de CRM en Notion"
    webhook_path = "notion-crm"

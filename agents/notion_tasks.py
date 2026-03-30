"""Agente de Notion Tasks — llama al AI Agent de n8n."""
from agents.base import BaseAgent

class NotionTasksAgent(BaseAgent):
    name = "notion_tasks"
    description = "Gestión de tareas en Notion"
    webhook_path = "notion-crm"

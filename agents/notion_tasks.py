"""Agente de notion_tasks — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class Notion_tasksAgent(BaseAgent):
    name = "notion_tasks"
    description = "Agente notion_tasks"
    webhook_path = "notion-tasks"

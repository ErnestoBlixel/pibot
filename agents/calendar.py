"""Agente de Google Calendar — llama al AI Agent de n8n."""

from agents.base import BaseAgent


class CalendarAgent(BaseAgent):
    name = "calendar"
    description = "Gestión de Google Calendar (Ernesto, Marta, Blixel)"
    webhook_path = "calendar"

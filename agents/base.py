"""
Clase base para agentes de PiBot.
Cada agente llama a un webhook de n8n que tiene un AI Agent con tools reales.
"""

from abc import ABC, abstractmethod
import json
import httpx
import structlog

from config import settings

logger = structlog.get_logger()


class BaseAgent(ABC):
    name: str = "base"
    description: str = "Agente base"
    webhook_path: str = ""  # Path del webhook en n8n, ej: "calendar"

    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Envía el mensaje al webhook de n8n y devuelve la respuesta."""
        if not self.webhook_path:
            return f"Agente {self.name} no tiene webhook configurado."

        url = f"{settings.N8N_BASE_URL}/webhook/{self.webhook_path}"
        payload = {
            "message": message,
            "text": message,
            "session_id": session_id,
            "channel": channel,
        }

        logger.info("agent_calling_n8n", agent=self.name, url=url)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            # El AI Agent de n8n devuelve el texto en diferentes campos
            if isinstance(data, dict):
                text = data.get("output", data.get("text", data.get("response", "")))
                if not text and "data" in data:
                    text = str(data["data"])
            elif isinstance(data, list) and data:
                text = data[0].get("output", data[0].get("text", str(data[0])))
            else:
                text = str(data)

            logger.info("agent_n8n_response", agent=self.name, chars=len(text))
            return text or "El agente no devolvió respuesta."

        except httpx.ConnectError:
            logger.error("agent_n8n_unreachable", agent=self.name, url=url)
            return f"No puedo conectar con el servicio de {self.name}. El servidor n8n no está disponible."
        except httpx.HTTPStatusError as e:
            logger.error("agent_n8n_http_error", agent=self.name, status=e.response.status_code)
            return f"Error al conectar con {self.name}: HTTP {e.response.status_code}"
        except json.JSONDecodeError:
            logger.error("agent_n8n_invalid_json", agent=self.name)
            return f"El agente {self.name} devolvió una respuesta no válida."
        except Exception as e:
            logger.error("agent_n8n_error", agent=self.name, error=str(e))
            return f"Error al procesar con {self.name}: {e}"

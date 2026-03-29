"""
Clase base para agentes de PiBot.
Todos los agentes especializados heredan de BaseAgent.
"""

from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Clase base abstracta para todos los agentes del sistema."""

    name: str = "base"
    description: str = "Agente base"

    @abstractmethod
    async def handle(self, message: str, session_id: str = "", channel: str = "api") -> str:
        """Procesa un mensaje y devuelve la respuesta como texto."""
        ...

    async def confirm_action(self, action_description: str, session_id: str) -> bool:
        """Solicita confirmación al usuario para acciones sensibles."""
        from security.confirmation import request_confirmation
        return await request_confirmation(action_description, session_id)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"

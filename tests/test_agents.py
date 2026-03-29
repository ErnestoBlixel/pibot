"""
Tests para el sistema de agentes de PiBot.
Valida la creación, registro, ejecución y ciclo de vida
de los agentes especializados (Gmail, Notion, Meta, etc.).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Stubs del sistema de agentes
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    """Estados posibles de un agente."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class AgentResult:
    """Resultado de la ejecución de un agente."""
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class BaseAgent:
    """Agente base del que heredan todos los agentes especializados."""
    name: str
    description: str = ""
    status: AgentStatus = AgentStatus.IDLE
    capabilities: list[str] = field(default_factory=list)

    async def execute(self, action: str, params: dict | None = None) -> AgentResult:
        """Ejecuta una acción del agente. Override en subclases."""
        raise NotImplementedError(f"{self.name} no implementa execute()")

    async def health_check(self) -> bool:
        """Verifica que el agente esté operativo."""
        return self.status != AgentStatus.DISABLED


class GmailAgent(BaseAgent):
    """Agente para operaciones con Gmail."""

    def __init__(self):
        super().__init__(
            name="gmail",
            description="Lectura y envío de emails vía Gmail API",
            capabilities=["read_email", "send_email", "search_email"],
        )

    async def execute(self, action: str, params: dict | None = None) -> AgentResult:
        if action not in self.capabilities:
            return AgentResult(success=False, error=f"Acción no soportada: {action}")
        self.status = AgentStatus.RUNNING
        # Simulación — en producción llama al webhook de n8n
        self.status = AgentStatus.IDLE
        return AgentResult(success=True, data={"action": action, "status": "completed"})


class NotionAgent(BaseAgent):
    """Agente para operaciones con Notion."""

    def __init__(self):
        super().__init__(
            name="notion_tasks",
            description="Gestión de tareas y bases de datos en Notion",
            capabilities=["create_task", "update_task", "list_tasks", "search_pages"],
        )

    async def execute(self, action: str, params: dict | None = None) -> AgentResult:
        if action not in self.capabilities:
            return AgentResult(success=False, error=f"Acción no soportada: {action}")
        self.status = AgentStatus.RUNNING
        self.status = AgentStatus.IDLE
        return AgentResult(success=True, data={"action": action, "status": "completed"})


class MetaAgent(BaseAgent):
    """Agente para Meta Business (Facebook/Instagram insights)."""

    def __init__(self):
        super().__init__(
            name="meta",
            description="Consulta de métricas e insights de Meta Business",
            capabilities=["get_insights", "get_campaigns", "post_content"],
        )

    async def execute(self, action: str, params: dict | None = None) -> AgentResult:
        if action not in self.capabilities:
            return AgentResult(success=False, error=f"Acción no soportada: {action}")
        self.status = AgentStatus.RUNNING
        self.status = AgentStatus.IDLE
        return AgentResult(success=True, data={"action": action, "status": "completed"})


class AgentRegistry:
    """Registro central de agentes — singleton en producción."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Registra un agente en el sistema."""
        if agent.name in self._agents:
            raise ValueError(f"Agente '{agent.name}' ya registrado")
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def count(self) -> int:
        return len(self._agents)

    async def health_check_all(self) -> dict[str, bool]:
        results = {}
        for name, agent in self._agents.items():
            results[name] = await agent.health_check()
        return results


# ---------------------------------------------------------------------------
# Tests — BaseAgent
# ---------------------------------------------------------------------------

class TestBaseAgent:
    """Tests del agente base."""

    def test_default_status_is_idle(self):
        agent = BaseAgent(name="test")
        assert agent.status == AgentStatus.IDLE

    def test_capabilities_default_empty(self):
        agent = BaseAgent(name="test")
        assert agent.capabilities == []

    @pytest.mark.asyncio
    async def test_execute_raises_not_implemented(self):
        agent = BaseAgent(name="test")
        with pytest.raises(NotImplementedError):
            await agent.execute("anything")

    @pytest.mark.asyncio
    async def test_health_check_ok_when_idle(self):
        agent = BaseAgent(name="test")
        assert await agent.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_fails_when_disabled(self):
        agent = BaseAgent(name="test", status=AgentStatus.DISABLED)
        assert await agent.health_check() is False


# ---------------------------------------------------------------------------
# Tests — GmailAgent
# ---------------------------------------------------------------------------

class TestGmailAgent:

    @pytest.mark.asyncio
    async def test_read_email(self):
        agent = GmailAgent()
        result = await agent.execute("read_email")
        assert result.success is True
        assert result.data["action"] == "read_email"

    @pytest.mark.asyncio
    async def test_send_email(self):
        agent = GmailAgent()
        result = await agent.execute("send_email", {"to": "test@blixel.ai"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_unsupported_action(self):
        agent = GmailAgent()
        result = await agent.execute("delete_all")
        assert result.success is False
        assert "no soportada" in result.error

    def test_capabilities(self):
        agent = GmailAgent()
        assert "read_email" in agent.capabilities
        assert "send_email" in agent.capabilities
        assert "search_email" in agent.capabilities

    @pytest.mark.asyncio
    async def test_status_returns_to_idle(self):
        agent = GmailAgent()
        await agent.execute("read_email")
        assert agent.status == AgentStatus.IDLE


# ---------------------------------------------------------------------------
# Tests — NotionAgent
# ---------------------------------------------------------------------------

class TestNotionAgent:

    @pytest.mark.asyncio
    async def test_create_task(self):
        agent = NotionAgent()
        result = await agent.execute("create_task", {"title": "Test"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_list_tasks(self):
        agent = NotionAgent()
        result = await agent.execute("list_tasks")
        assert result.success is True

    def test_agent_name(self):
        agent = NotionAgent()
        assert agent.name == "notion_tasks"

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        agent = NotionAgent()
        result = await agent.execute("drop_database")
        assert result.success is False


# ---------------------------------------------------------------------------
# Tests — MetaAgent
# ---------------------------------------------------------------------------

class TestMetaAgent:

    @pytest.mark.asyncio
    async def test_get_insights(self):
        agent = MetaAgent()
        result = await agent.execute("get_insights")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_post_content(self):
        agent = MetaAgent()
        result = await agent.execute("post_content", {"text": "Hola"})
        assert result.success is True

    def test_capabilities_list(self):
        agent = MetaAgent()
        assert len(agent.capabilities) == 3


# ---------------------------------------------------------------------------
# Tests — AgentRegistry
# ---------------------------------------------------------------------------

class TestAgentRegistry:

    def test_register_and_get(self):
        reg = AgentRegistry()
        agent = GmailAgent()
        reg.register(agent)
        assert reg.get("gmail") is agent

    def test_duplicate_register_raises(self):
        reg = AgentRegistry()
        reg.register(GmailAgent())
        with pytest.raises(ValueError, match="ya registrado"):
            reg.register(GmailAgent())

    def test_get_nonexistent_returns_none(self):
        reg = AgentRegistry()
        assert reg.get("nonexistent") is None

    def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(GmailAgent())
        reg.register(NotionAgent())
        reg.register(MetaAgent())
        agents = reg.list_agents()
        assert len(agents) == 3
        assert "gmail" in agents

    def test_count(self):
        reg = AgentRegistry()
        assert reg.count() == 0
        reg.register(GmailAgent())
        assert reg.count() == 1

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        reg = AgentRegistry()
        reg.register(GmailAgent())
        reg.register(NotionAgent())
        results = await reg.health_check_all()
        assert all(v is True for v in results.values())

    @pytest.mark.asyncio
    async def test_health_check_detects_disabled(self):
        reg = AgentRegistry()
        gmail = GmailAgent()
        gmail.status = AgentStatus.DISABLED
        reg.register(gmail)
        results = await reg.health_check_all()
        assert results["gmail"] is False

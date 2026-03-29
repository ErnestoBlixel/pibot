"""
Tests para el orquestador de PiBot.
Valida el enrutamiento de intenciones, la ejecución de planes
multi-step, la gestión de confirmaciones y el manejo de errores.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Stubs del orquestador
# ---------------------------------------------------------------------------

class IntentType(str, Enum):
    """Tipos de intención que el orquestador reconoce."""
    QUERY = "query"
    ACTION = "action"
    MULTI_STEP = "multi_step"
    CONFIRMATION = "confirmation"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Intención parseada del mensaje del usuario."""
    type: IntentType
    agent: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class PlanStep:
    """Un paso dentro de un plan multi-step."""
    agent: str
    action: str
    params: dict = field(default_factory=dict)
    requires_confirmation: bool = False
    depends_on: Optional[int] = None  # índice del paso previo


@dataclass
class PlanResult:
    """Resultado de ejecutar un plan completo."""
    success: bool
    steps_completed: int = 0
    steps_total: int = 0
    results: list[dict] = field(default_factory=list)
    error: Optional[str] = None


class IntentRouter:
    """Clasifica el mensaje del usuario en una intención enrutable."""

    # Mapeo simple de keywords a agentes
    KEYWORD_MAP = {
        "email": ("gmail", "read_email"),
        "correo": ("gmail", "read_email"),
        "enviar email": ("gmail", "send_email"),
        "tarea": ("notion_tasks", "create_task"),
        "tareas": ("notion_tasks", "list_tasks"),
        "insights": ("meta", "get_insights"),
        "métricas": ("meta", "get_insights"),
        "factura": ("holded", "list_invoices"),
        "facturas": ("holded", "list_invoices"),
        "calendario": ("calendar", "get_today"),
        "agenda": ("calendar", "get_today"),
    }

    def classify(self, message: str) -> Intent:
        """Clasifica un mensaje en una intención."""
        msg_lower = message.lower().strip()

        if not msg_lower:
            return Intent(type=IntentType.UNKNOWN)

        # Respuestas de confirmación
        if msg_lower in ("sí", "si", "ok", "confirmar", "adelante"):
            return Intent(type=IntentType.CONFIRMATION, confidence=0.95)

        # Buscar keywords
        for keyword, (agent, action) in self.KEYWORD_MAP.items():
            if keyword in msg_lower:
                return Intent(
                    type=IntentType.ACTION,
                    agent=agent,
                    action=action,
                    confidence=0.8,
                )

        # Si contiene "?" es una query
        if "?" in msg_lower:
            return Intent(type=IntentType.QUERY, confidence=0.6)

        return Intent(type=IntentType.UNKNOWN, confidence=0.0)


class PlanExecutor:
    """Ejecuta planes multi-step con soporte de confirmación."""

    def __init__(self, agent_executor: Any = None):
        self._executor = agent_executor or AsyncMock()
        self._pending_confirmation: Optional[PlanStep] = None

    async def execute_plan(self, steps: list[PlanStep], auto_confirm: bool = False) -> PlanResult:
        """Ejecuta una lista de pasos secuencialmente."""
        results = []
        for i, step in enumerate(steps):
            # Si requiere confirmación y no es auto-confirm, pausar
            if step.requires_confirmation and not auto_confirm:
                self._pending_confirmation = step
                return PlanResult(
                    success=True,
                    steps_completed=i,
                    steps_total=len(steps),
                    results=results,
                    error="awaiting_confirmation",
                )
            try:
                result = await self._executor(step.agent, step.action, step.params)
                results.append({"step": i, "agent": step.agent, "result": result})
            except Exception as e:
                return PlanResult(
                    success=False,
                    steps_completed=i,
                    steps_total=len(steps),
                    results=results,
                    error=str(e),
                )

        return PlanResult(
            success=True,
            steps_completed=len(steps),
            steps_total=len(steps),
            results=results,
        )

    async def confirm_pending(self) -> PlanResult | None:
        """Confirma y ejecuta el paso pendiente."""
        if not self._pending_confirmation:
            return None
        step = self._pending_confirmation
        self._pending_confirmation = None
        result = await self._executor(step.agent, step.action, step.params)
        return PlanResult(
            success=True,
            steps_completed=1,
            steps_total=1,
            results=[{"step": 0, "agent": step.agent, "result": result}],
        )


# ---------------------------------------------------------------------------
# Tests — IntentRouter
# ---------------------------------------------------------------------------

class TestIntentRouter:
    """Tests del clasificador de intenciones."""

    def setup_method(self):
        self.router = IntentRouter()

    def test_classify_email(self):
        intent = self.router.classify("Lee mis emails de hoy")
        assert intent.type == IntentType.ACTION
        assert intent.agent == "gmail"
        assert intent.action == "read_email"

    def test_classify_tarea(self):
        intent = self.router.classify("Crea una tarea en Notion")
        assert intent.type == IntentType.ACTION
        assert intent.agent == "notion_tasks"

    def test_classify_insights(self):
        intent = self.router.classify("Dame los insights de Instagram")
        assert intent.type == IntentType.ACTION
        assert intent.agent == "meta"
        assert intent.action == "get_insights"

    def test_classify_factura(self):
        intent = self.router.classify("Muéstrame las facturas pendientes")
        assert intent.type == IntentType.ACTION
        assert intent.agent == "holded"

    def test_classify_calendario(self):
        intent = self.router.classify("¿Qué tengo en el calendario?")
        assert intent.type == IntentType.ACTION
        assert intent.agent == "calendar"

    def test_classify_confirmation(self):
        for word in ["sí", "ok", "confirmar"]:
            intent = self.router.classify(word)
            assert intent.type == IntentType.CONFIRMATION

    def test_classify_question(self):
        intent = self.router.classify("¿Cuánto facturamos este mes?")
        # Contiene "factura" keyword, se resuelve como acción
        assert intent.type == IntentType.ACTION

    def test_classify_pure_question(self):
        intent = self.router.classify("¿Cómo estás?")
        assert intent.type == IntentType.QUERY

    def test_classify_unknown(self):
        intent = self.router.classify("asdfghjkl")
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence == 0.0

    def test_classify_empty(self):
        intent = self.router.classify("")
        assert intent.type == IntentType.UNKNOWN

    def test_confidence_above_zero_for_match(self):
        intent = self.router.classify("enviar email a Marta")
        assert intent.confidence > 0

    def test_correo_synonym(self):
        intent = self.router.classify("Revisa el correo")
        assert intent.agent == "gmail"


# ---------------------------------------------------------------------------
# Tests — PlanExecutor
# ---------------------------------------------------------------------------

class TestPlanExecutor:

    @pytest.mark.asyncio
    async def test_single_step_plan(self):
        executor_fn = AsyncMock(return_value={"ok": True})
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [PlanStep(agent="gmail", action="read_email")]
        result = await planner.execute_plan(steps)
        assert result.success is True
        assert result.steps_completed == 1

    @pytest.mark.asyncio
    async def test_multi_step_plan(self):
        executor_fn = AsyncMock(return_value={"ok": True})
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [
            PlanStep(agent="gmail", action="read_email"),
            PlanStep(agent="notion_tasks", action="create_task"),
            PlanStep(agent="meta", action="get_insights"),
        ]
        result = await planner.execute_plan(steps)
        assert result.success is True
        assert result.steps_completed == 3
        assert result.steps_total == 3

    @pytest.mark.asyncio
    async def test_confirmation_pauses_execution(self):
        executor_fn = AsyncMock(return_value={"ok": True})
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [
            PlanStep(agent="gmail", action="read_email"),
            PlanStep(agent="gmail", action="send_email", requires_confirmation=True),
        ]
        result = await planner.execute_plan(steps)
        assert result.steps_completed == 1
        assert result.error == "awaiting_confirmation"

    @pytest.mark.asyncio
    async def test_auto_confirm_skips_pause(self):
        executor_fn = AsyncMock(return_value={"ok": True})
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [
            PlanStep(agent="gmail", action="send_email", requires_confirmation=True),
        ]
        result = await planner.execute_plan(steps, auto_confirm=True)
        assert result.success is True
        assert result.steps_completed == 1

    @pytest.mark.asyncio
    async def test_confirm_pending(self):
        executor_fn = AsyncMock(return_value={"sent": True})
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [
            PlanStep(agent="gmail", action="send_email", requires_confirmation=True),
        ]
        await planner.execute_plan(steps)
        result = await planner.confirm_pending()
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_confirm_when_nothing_pending(self):
        planner = PlanExecutor()
        result = await planner.confirm_pending()
        assert result is None

    @pytest.mark.asyncio
    async def test_step_failure_stops_plan(self):
        executor_fn = AsyncMock(side_effect=RuntimeError("n8n timeout"))
        planner = PlanExecutor(agent_executor=executor_fn)
        steps = [
            PlanStep(agent="gmail", action="read_email"),
            PlanStep(agent="notion_tasks", action="create_task"),
        ]
        result = await planner.execute_plan(steps)
        assert result.success is False
        assert result.steps_completed == 0
        assert "n8n timeout" in result.error

    @pytest.mark.asyncio
    async def test_empty_plan(self):
        planner = PlanExecutor()
        result = await planner.execute_plan([])
        assert result.success is True
        assert result.steps_completed == 0

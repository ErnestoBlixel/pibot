"""
Tests para el sistema proactivo de PiBot.
Valida triggers, reglas de automatización, programación
de tareas y alertas del sistema.
"""

import time
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Stubs del sistema proactivo
# ---------------------------------------------------------------------------

class TriggerType(str, Enum):
    """Tipos de trigger para acciones proactivas."""
    SCHEDULE = "schedule"       # Cron-like
    EVENT = "event"             # Reactivo a eventos
    THRESHOLD = "threshold"     # Cuando un valor cruza un umbral
    PATTERN = "pattern"         # Cuando se detecta un patrón


@dataclass
class ProactiveTrigger:
    """Definición de un trigger proactivo."""
    name: str
    type: TriggerType
    condition: str
    action_agent: str
    action_skill: str
    params: dict = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: int = 300  # Mínimo tiempo entre ejecuciones
    last_fired: float = 0.0


@dataclass
class Alert:
    """Alerta generada por el sistema proactivo."""
    level: str  # info, warning, critical
    source: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class ProactiveEngine:
    """Motor de acciones proactivas del sistema."""

    def __init__(self):
        self._triggers: dict[str, ProactiveTrigger] = {}
        self._alerts: list[Alert] = []
        self._executor: Optional[Callable] = None

    def set_executor(self, executor: Callable) -> None:
        """Establece la función que ejecuta acciones."""
        self._executor = executor

    def add_trigger(self, trigger: ProactiveTrigger) -> None:
        self._triggers[trigger.name] = trigger

    def remove_trigger(self, name: str) -> bool:
        if name in self._triggers:
            del self._triggers[name]
            return True
        return False

    def get_trigger(self, name: str) -> ProactiveTrigger | None:
        return self._triggers.get(name)

    def list_triggers(self) -> list[ProactiveTrigger]:
        return list(self._triggers.values())

    def list_enabled_triggers(self) -> list[ProactiveTrigger]:
        return [t for t in self._triggers.values() if t.enabled]

    async def evaluate_trigger(self, trigger_name: str, context: dict | None = None) -> bool:
        """Evalúa si un trigger debe dispararse y lo ejecuta si procede."""
        trigger = self._triggers.get(trigger_name)
        if not trigger or not trigger.enabled:
            return False

        now = time.time()
        if now - trigger.last_fired < trigger.cooldown_seconds:
            return False  # Cooldown activo

        # Ejecutar acción
        if self._executor:
            await self._executor(trigger.action_agent, trigger.action_skill, trigger.params)

        trigger.last_fired = now
        return True

    def add_alert(self, level: str, source: str, message: str) -> Alert:
        alert = Alert(level=level, source=source, message=message)
        self._alerts.append(alert)
        return alert

    def get_alerts(self, unacknowledged_only: bool = False) -> list[Alert]:
        if unacknowledged_only:
            return [a for a in self._alerts if not a.acknowledged]
        return list(self._alerts)

    def acknowledge_alert(self, index: int) -> bool:
        if 0 <= index < len(self._alerts):
            self._alerts[index].acknowledged = True
            return True
        return False

    def get_critical_alerts(self) -> list[Alert]:
        return [a for a in self._alerts if a.level == "critical" and not a.acknowledged]


# ---------------------------------------------------------------------------
# Tests — ProactiveTrigger
# ---------------------------------------------------------------------------

class TestProactiveTrigger:

    def test_default_enabled(self):
        trigger = ProactiveTrigger(
            name="test", type=TriggerType.SCHEDULE,
            condition="0 9 * * *", action_agent="gmail", action_skill="read_email"
        )
        assert trigger.enabled is True

    def test_default_cooldown(self):
        trigger = ProactiveTrigger(
            name="test", type=TriggerType.SCHEDULE,
            condition="0 9 * * *", action_agent="gmail", action_skill="read_email"
        )
        assert trigger.cooldown_seconds == 300

    def test_custom_cooldown(self):
        trigger = ProactiveTrigger(
            name="test", type=TriggerType.THRESHOLD,
            condition="errors > 10", action_agent="meta", action_skill="get_insights",
            cooldown_seconds=60,
        )
        assert trigger.cooldown_seconds == 60

    def test_last_fired_initially_zero(self):
        trigger = ProactiveTrigger(
            name="test", type=TriggerType.EVENT,
            condition="new_email", action_agent="gmail", action_skill="read_email"
        )
        assert trigger.last_fired == 0.0


# ---------------------------------------------------------------------------
# Tests — ProactiveEngine triggers
# ---------------------------------------------------------------------------

class TestProactiveEngineTriggers:

    def test_add_and_get_trigger(self):
        engine = ProactiveEngine()
        trigger = ProactiveTrigger(
            name="morning_email", type=TriggerType.SCHEDULE,
            condition="0 9 * * *", action_agent="gmail", action_skill="read_email"
        )
        engine.add_trigger(trigger)
        assert engine.get_trigger("morning_email") is trigger

    def test_remove_trigger(self):
        engine = ProactiveEngine()
        trigger = ProactiveTrigger(
            name="t1", type=TriggerType.EVENT,
            condition="x", action_agent="a", action_skill="b"
        )
        engine.add_trigger(trigger)
        assert engine.remove_trigger("t1") is True
        assert engine.get_trigger("t1") is None

    def test_remove_nonexistent(self):
        engine = ProactiveEngine()
        assert engine.remove_trigger("nope") is False

    def test_list_triggers(self):
        engine = ProactiveEngine()
        for i in range(3):
            engine.add_trigger(ProactiveTrigger(
                name=f"t{i}", type=TriggerType.SCHEDULE,
                condition="*", action_agent="a", action_skill="b"
            ))
        assert len(engine.list_triggers()) == 3

    def test_list_enabled_triggers(self):
        engine = ProactiveEngine()
        engine.add_trigger(ProactiveTrigger(
            name="t1", type=TriggerType.SCHEDULE,
            condition="*", action_agent="a", action_skill="b", enabled=True
        ))
        engine.add_trigger(ProactiveTrigger(
            name="t2", type=TriggerType.SCHEDULE,
            condition="*", action_agent="a", action_skill="b", enabled=False
        ))
        assert len(engine.list_enabled_triggers()) == 1

    @pytest.mark.asyncio
    async def test_evaluate_trigger_fires(self):
        engine = ProactiveEngine()
        executor = AsyncMock()
        engine.set_executor(executor)
        engine.add_trigger(ProactiveTrigger(
            name="t1", type=TriggerType.EVENT,
            condition="new_email", action_agent="gmail", action_skill="read_email"
        ))
        result = await engine.evaluate_trigger("t1")
        assert result is True
        executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_disabled_trigger(self):
        engine = ProactiveEngine()
        executor = AsyncMock()
        engine.set_executor(executor)
        engine.add_trigger(ProactiveTrigger(
            name="t1", type=TriggerType.EVENT,
            condition="x", action_agent="a", action_skill="b", enabled=False
        ))
        result = await engine.evaluate_trigger("t1")
        assert result is False
        executor.assert_not_called()

    @pytest.mark.asyncio
    async def test_evaluate_nonexistent_trigger(self):
        engine = ProactiveEngine()
        result = await engine.evaluate_trigger("nope")
        assert result is False

    @pytest.mark.asyncio
    async def test_cooldown_prevents_rapid_firing(self):
        engine = ProactiveEngine()
        executor = AsyncMock()
        engine.set_executor(executor)
        engine.add_trigger(ProactiveTrigger(
            name="t1", type=TriggerType.EVENT,
            condition="x", action_agent="a", action_skill="b",
            cooldown_seconds=3600,
        ))
        # Primera ejecución OK
        assert await engine.evaluate_trigger("t1") is True
        # Segunda bloqueada por cooldown
        assert await engine.evaluate_trigger("t1") is False

    @pytest.mark.asyncio
    async def test_cooldown_expired_allows_firing(self):
        engine = ProactiveEngine()
        executor = AsyncMock()
        engine.set_executor(executor)
        trigger = ProactiveTrigger(
            name="t1", type=TriggerType.EVENT,
            condition="x", action_agent="a", action_skill="b",
            cooldown_seconds=1,
        )
        engine.add_trigger(trigger)
        await engine.evaluate_trigger("t1")
        # Simular que pasó el cooldown
        trigger.last_fired = time.time() - 2
        assert await engine.evaluate_trigger("t1") is True


# ---------------------------------------------------------------------------
# Tests — Alertas
# ---------------------------------------------------------------------------

class TestProactiveEngineAlerts:

    def test_add_alert(self):
        engine = ProactiveEngine()
        alert = engine.add_alert("warning", "meta", "API rate limit cerca del umbral")
        assert alert.level == "warning"
        assert alert.source == "meta"
        assert alert.acknowledged is False

    def test_get_all_alerts(self):
        engine = ProactiveEngine()
        engine.add_alert("info", "system", "Inicio")
        engine.add_alert("warning", "gmail", "Token próximo a expirar")
        assert len(engine.get_alerts()) == 2

    def test_get_unacknowledged_alerts(self):
        engine = ProactiveEngine()
        engine.add_alert("info", "system", "a")
        engine.add_alert("warning", "gmail", "b")
        engine.acknowledge_alert(0)
        unack = engine.get_alerts(unacknowledged_only=True)
        assert len(unack) == 1
        assert unack[0].message == "b"

    def test_acknowledge_alert(self):
        engine = ProactiveEngine()
        engine.add_alert("critical", "holded", "Error de facturación")
        assert engine.acknowledge_alert(0) is True
        assert engine.get_alerts()[0].acknowledged is True

    def test_acknowledge_invalid_index(self):
        engine = ProactiveEngine()
        assert engine.acknowledge_alert(99) is False

    def test_critical_alerts(self):
        engine = ProactiveEngine()
        engine.add_alert("info", "system", "ok")
        engine.add_alert("critical", "holded", "fallo")
        engine.add_alert("critical", "gmail", "token expirado")
        critical = engine.get_critical_alerts()
        assert len(critical) == 2

    def test_critical_alerts_exclude_acknowledged(self):
        engine = ProactiveEngine()
        engine.add_alert("critical", "holded", "fallo")
        engine.acknowledge_alert(0)
        assert len(engine.get_critical_alerts()) == 0

    def test_alert_has_timestamp(self):
        engine = ProactiveEngine()
        alert = engine.add_alert("info", "system", "test")
        assert alert.timestamp > 0

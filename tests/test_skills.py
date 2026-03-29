"""
Tests para el sistema de skills de PiBot.
Valida el registro, ejecución y descubrimiento de skills
que los agentes pueden invocar.
"""

import pytest
from unittest.mock import AsyncMock
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Stubs del sistema de skills
# ---------------------------------------------------------------------------

@dataclass
class SkillDefinition:
    """Definición de un skill disponible en el sistema."""
    name: str
    description: str
    agent: str
    parameters: list[dict] = field(default_factory=list)
    requires_confirmation: bool = False
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


class SkillRegistry:
    """Registro centralizado de skills del sistema."""

    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def list_enabled(self) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.enabled]

    def list_by_agent(self, agent: str) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if s.agent == agent]

    def list_by_tag(self, tag: str) -> list[SkillDefinition]:
        return [s for s in self._skills.values() if tag in s.tags]

    def search(self, query: str) -> list[SkillDefinition]:
        """Búsqueda simple por nombre o descripción."""
        q = query.lower()
        return [
            s for s in self._skills.values()
            if q in s.name.lower() or q in s.description.lower()
        ]

    def disable(self, name: str) -> bool:
        skill = self._skills.get(name)
        if skill:
            skill.enabled = False
            return True
        return False

    def enable(self, name: str) -> bool:
        skill = self._skills.get(name)
        if skill:
            skill.enabled = True
            return True
        return False


def build_default_registry() -> SkillRegistry:
    """Construye el registry con los skills por defecto de PiBot."""
    reg = SkillRegistry()

    skills = [
        SkillDefinition(
            name="gmail.read_email",
            description="Lee los emails recientes del buzón",
            agent="gmail",
            tags=["email", "lectura"],
        ),
        SkillDefinition(
            name="gmail.send_email",
            description="Envía un email desde la cuenta configurada",
            agent="gmail",
            requires_confirmation=True,
            parameters=[{"name": "to", "type": "string", "required": True}],
            tags=["email", "escritura"],
        ),
        SkillDefinition(
            name="notion_tasks.create_task",
            description="Crea una tarea nueva en Notion",
            agent="notion_tasks",
            requires_confirmation=True,
            parameters=[{"name": "title", "type": "string", "required": True}],
            tags=["tareas", "escritura"],
        ),
        SkillDefinition(
            name="notion_tasks.list_tasks",
            description="Lista las tareas pendientes de Notion",
            agent="notion_tasks",
            tags=["tareas", "lectura"],
        ),
        SkillDefinition(
            name="meta.get_insights",
            description="Obtiene métricas de Meta Business",
            agent="meta",
            tags=["analytics", "lectura"],
        ),
        SkillDefinition(
            name="holded.list_invoices",
            description="Lista las facturas de Holded",
            agent="holded",
            tags=["facturación", "lectura"],
        ),
        SkillDefinition(
            name="calendar.get_today",
            description="Obtiene los eventos del día de Google Calendar",
            agent="calendar",
            tags=["calendario", "lectura"],
        ),
        SkillDefinition(
            name="calendar.create_event",
            description="Crea un evento en Google Calendar",
            agent="calendar",
            requires_confirmation=True,
            parameters=[
                {"name": "title", "type": "string", "required": True},
                {"name": "start", "type": "datetime", "required": True},
            ],
            tags=["calendario", "escritura"],
        ),
    ]

    for skill in skills:
        reg.register(skill)

    return reg


# ---------------------------------------------------------------------------
# Tests — SkillDefinition
# ---------------------------------------------------------------------------

class TestSkillDefinition:

    def test_default_enabled(self):
        skill = SkillDefinition(name="test", description="Test", agent="test")
        assert skill.enabled is True

    def test_no_confirmation_by_default(self):
        skill = SkillDefinition(name="test", description="Test", agent="test")
        assert skill.requires_confirmation is False

    def test_empty_parameters_by_default(self):
        skill = SkillDefinition(name="test", description="Test", agent="test")
        assert skill.parameters == []

    def test_tags(self):
        skill = SkillDefinition(
            name="test", description="Test", agent="test", tags=["a", "b"]
        )
        assert "a" in skill.tags


# ---------------------------------------------------------------------------
# Tests — SkillRegistry
# ---------------------------------------------------------------------------

class TestSkillRegistry:

    def test_register_and_get(self):
        reg = SkillRegistry()
        skill = SkillDefinition(name="test.skill", description="Test", agent="test")
        reg.register(skill)
        assert reg.get("test.skill") is skill

    def test_get_nonexistent(self):
        reg = SkillRegistry()
        assert reg.get("nope") is None

    def test_list_all(self):
        reg = build_default_registry()
        all_skills = reg.list_all()
        assert len(all_skills) == 8

    def test_list_enabled_excludes_disabled(self):
        reg = build_default_registry()
        reg.disable("gmail.read_email")
        enabled = reg.list_enabled()
        names = [s.name for s in enabled]
        assert "gmail.read_email" not in names
        assert len(enabled) == 7

    def test_list_by_agent(self):
        reg = build_default_registry()
        gmail_skills = reg.list_by_agent("gmail")
        assert len(gmail_skills) == 2
        assert all(s.agent == "gmail" for s in gmail_skills)

    def test_list_by_agent_no_match(self):
        reg = build_default_registry()
        assert reg.list_by_agent("slack") == []

    def test_list_by_tag(self):
        reg = build_default_registry()
        write_skills = reg.list_by_tag("escritura")
        assert len(write_skills) >= 3
        assert all("escritura" in s.tags for s in write_skills)

    def test_search_by_name(self):
        reg = build_default_registry()
        results = reg.search("gmail")
        assert len(results) == 2

    def test_search_by_description(self):
        reg = build_default_registry()
        results = reg.search("métricas")
        assert len(results) >= 1
        assert results[0].name == "meta.get_insights"

    def test_search_case_insensitive(self):
        reg = build_default_registry()
        results = reg.search("NOTION")
        assert len(results) >= 2

    def test_search_no_results(self):
        reg = build_default_registry()
        assert reg.search("zzzzzzz") == []

    def test_disable_skill(self):
        reg = build_default_registry()
        assert reg.disable("gmail.read_email") is True
        skill = reg.get("gmail.read_email")
        assert skill.enabled is False

    def test_disable_nonexistent(self):
        reg = SkillRegistry()
        assert reg.disable("nope") is False

    def test_enable_skill(self):
        reg = build_default_registry()
        reg.disable("gmail.read_email")
        assert reg.enable("gmail.read_email") is True
        assert reg.get("gmail.read_email").enabled is True

    def test_overwrite_skill(self):
        """Registrar un skill con el mismo nombre lo sobreescribe."""
        reg = SkillRegistry()
        s1 = SkillDefinition(name="x", description="v1", agent="a")
        s2 = SkillDefinition(name="x", description="v2", agent="a")
        reg.register(s1)
        reg.register(s2)
        assert reg.get("x").description == "v2"


# ---------------------------------------------------------------------------
# Tests — Default Registry
# ---------------------------------------------------------------------------

class TestDefaultRegistry:

    def test_has_gmail_skills(self):
        reg = build_default_registry()
        assert reg.get("gmail.read_email") is not None
        assert reg.get("gmail.send_email") is not None

    def test_has_notion_skills(self):
        reg = build_default_registry()
        assert reg.get("notion_tasks.create_task") is not None
        assert reg.get("notion_tasks.list_tasks") is not None

    def test_has_meta_skills(self):
        reg = build_default_registry()
        assert reg.get("meta.get_insights") is not None

    def test_has_holded_skills(self):
        reg = build_default_registry()
        assert reg.get("holded.list_invoices") is not None

    def test_has_calendar_skills(self):
        reg = build_default_registry()
        assert reg.get("calendar.get_today") is not None
        assert reg.get("calendar.create_event") is not None

    def test_send_email_requires_confirmation(self):
        reg = build_default_registry()
        skill = reg.get("gmail.send_email")
        assert skill.requires_confirmation is True

    def test_read_email_no_confirmation(self):
        reg = build_default_registry()
        skill = reg.get("gmail.read_email")
        assert skill.requires_confirmation is False

    def test_create_event_has_parameters(self):
        reg = build_default_registry()
        skill = reg.get("calendar.create_event")
        assert len(skill.parameters) == 2
        param_names = [p["name"] for p in skill.parameters]
        assert "title" in param_names
        assert "start" in param_names

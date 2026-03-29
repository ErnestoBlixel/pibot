"""
Sistema de skills para PiBot.
Registro y descubrimiento de habilidades especializadas.
"""

import structlog

logger = structlog.get_logger()

_SKILLS: dict[str, dict] = {}


def register_skill(name: str, description: str, handler, category: str = "general") -> None:
    """Registra una skill en el sistema."""
    _SKILLS[name] = {
        "name": name,
        "description": description,
        "handler": handler,
        "category": category,
    }
    logger.info("skill_registered", name=name, category=category)


def list_skills() -> list[dict]:
    """Devuelve la lista de skills registradas (sin el handler)."""
    return [
        {"name": s["name"], "description": s["description"], "category": s["category"]}
        for s in _SKILLS.values()
    ]


def get_skill(name: str):
    """Devuelve una skill por nombre o None."""
    entry = _SKILLS.get(name)
    return entry["handler"] if entry else None


async def execute_skill(name: str, **kwargs) -> str:
    """Ejecuta una skill por nombre."""
    handler = get_skill(name)
    if not handler:
        return f"Skill '{name}' no encontrada."
    try:
        result = await handler(**kwargs)
        return result
    except Exception as e:
        logger.error("skill_error", name=name, error=str(e))
        return f"Error ejecutando skill '{name}': {e}"

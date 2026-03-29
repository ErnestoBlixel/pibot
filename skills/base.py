"""
Sistema de skills para PiBot.
Cada skill es un experto con system prompt, triggers y acceso a memoria.
"""

from dataclasses import dataclass, field

import structlog

from orchestrator.llm import chat_completion

logger = structlog.get_logger()

_SKILLS: dict[str, "Skill"] = {}


@dataclass
class Skill:
    name: str
    description: str
    system_prompt: str
    triggers: list[str] = field(default_factory=list)

    async def execute(self, user_message: str, context: list[dict] | None = None) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        if context:
            messages.extend(context[-4:])
        messages.append({"role": "user", "content": user_message})
        return await chat_completion(messages, temperature=0.3)


def register_skill(skill: Skill) -> None:
    _SKILLS[skill.name] = skill


def list_skills() -> list[dict]:
    return [{"name": s.name, "description": s.description} for s in _SKILLS.values()]


def get_skill(name: str) -> Skill | None:
    return _SKILLS.get(name)


def match_skill(message: str) -> Skill | None:
    msg_lower = message.lower()
    for skill in _SKILLS.values():
        for trigger in skill.triggers:
            if trigger in msg_lower:
                return skill
    return None

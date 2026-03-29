"""
Cliente LLM centralizado para PiBot.
Todas las llamadas al modelo pasan por aquí.
"""

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """Envía mensajes al LLM vía OpenRouter y devuelve el texto de respuesta."""
    model = model or settings.OPENROUTER_MODEL

    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://blixel.ai",
        "X-Title": "PiBot",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    text = choice["message"]["content"] or ""
    logger.debug("llm_response", model=model, tokens=data.get("usage", {}))
    return text.strip()

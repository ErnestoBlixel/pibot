"""
Servicio de Text-to-Speech para PiBot.
Sintetiza texto a audio usando OpenAI TTS.
"""

import uuid
from pathlib import Path

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

AUDIO_DIR = Path("static/audio")


async def synthesize(text: str, voice: str | None = None) -> str:
    """Sintetiza texto a audio y devuelve la URL del archivo."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada para TTS")

    voice = voice or settings.TTS_VOICE
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = AUDIO_DIR / filename

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "tts-1",
                "input": text[:4096],
                "voice": voice,
            },
        )
        resp.raise_for_status()
        filepath.write_bytes(resp.content)

    url = f"/static/audio/{filename}"
    logger.info("tts_synthesized", voice=voice, chars=len(text), file=filename)
    return url

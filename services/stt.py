"""
Servicio de Speech-to-Text para PiBot.
Transcribe audio a texto usando OpenAI Whisper.
"""

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


async def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribe audio a texto usando la API de Whisper."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no configurada para STT")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            files={"file": (filename, audio_bytes, "audio/ogg")},
            data={"model": "whisper-1", "language": "es"},
        )
        resp.raise_for_status()
        data = resp.json()

    text = data.get("text", "").strip()
    logger.info("stt_transcribed", chars=len(text))
    return text

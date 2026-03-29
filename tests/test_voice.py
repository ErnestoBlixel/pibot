"""
Tests para el sistema de voz de PiBot.
Valida la transcripción (STT), síntesis (TTS),
procesamiento de audio y el pipeline completo de voz.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ---------------------------------------------------------------------------
# Stubs del sistema de voz
# ---------------------------------------------------------------------------

class AudioFormat(str, Enum):
    """Formatos de audio soportados."""
    OGG = "ogg"
    MP3 = "mp3"
    WAV = "wav"
    WEBM = "webm"


@dataclass
class TranscriptionResult:
    """Resultado de transcripción STT."""
    text: str
    language: str = "es"
    confidence: float = 0.0
    duration_seconds: float = 0.0


@dataclass
class SynthesisResult:
    """Resultado de síntesis TTS."""
    audio_bytes: bytes = b""
    format: AudioFormat = AudioFormat.MP3
    duration_seconds: float = 0.0


class AudioProcessor:
    """Procesador de audio — convierte formatos y valida archivos."""

    SUPPORTED_FORMATS = {AudioFormat.OGG, AudioFormat.MP3, AudioFormat.WAV, AudioFormat.WEBM}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    MAX_DURATION = 300  # 5 minutos

    def validate_file(self, data: bytes, format: AudioFormat) -> tuple[bool, str]:
        """Valida un archivo de audio antes de procesarlo."""
        if not data:
            return False, "Archivo vacío"
        if len(data) > self.MAX_FILE_SIZE:
            return False, f"Archivo demasiado grande ({len(data)} bytes, máx {self.MAX_FILE_SIZE})"
        if format not in self.SUPPORTED_FORMATS:
            return False, f"Formato no soportado: {format}"
        return True, "ok"

    def estimate_duration(self, data: bytes, format: AudioFormat) -> float:
        """Estima la duración del audio basándose en el tamaño."""
        # Estimación simple por bitrate medio según formato
        bitrate_map = {
            AudioFormat.OGG: 128000 / 8,   # 128 kbps
            AudioFormat.MP3: 192000 / 8,    # 192 kbps
            AudioFormat.WAV: 1411000 / 8,   # 1411 kbps (CD quality)
            AudioFormat.WEBM: 128000 / 8,   # 128 kbps
        }
        bytes_per_second = bitrate_map.get(format, 128000 / 8)
        return len(data) / bytes_per_second


class STTProvider:
    """Proveedor de Speech-to-Text (mock para tests)."""

    def __init__(self, provider: str = "openai"):
        self.provider = provider

    async def transcribe(self, audio_data: bytes, format: AudioFormat) -> TranscriptionResult:
        """Transcribe audio a texto."""
        if not audio_data:
            raise ValueError("No hay datos de audio para transcribir")
        # En producción llama a OpenAI Whisper
        return TranscriptionResult(
            text="Texto transcrito de prueba",
            language="es",
            confidence=0.95,
            duration_seconds=3.5,
        )


class TTSProvider:
    """Proveedor de Text-to-Speech (mock para tests)."""

    AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(self, provider: str = "openai", voice: str = "alloy"):
        self.provider = provider
        self.voice = voice

    async def synthesize(self, text: str) -> SynthesisResult:
        """Sintetiza texto a audio."""
        if not text or not text.strip():
            raise ValueError("No hay texto para sintetizar")
        # En producción llama a OpenAI TTS
        fake_audio = b"\x00\x01\x02" * 100
        return SynthesisResult(
            audio_bytes=fake_audio,
            format=AudioFormat.MP3,
            duration_seconds=len(text) * 0.06,  # ~60ms por carácter
        )

    def set_voice(self, voice: str) -> None:
        if voice not in self.AVAILABLE_VOICES:
            raise ValueError(f"Voz no disponible: {voice}")
        self.voice = voice


class VoicePipeline:
    """Pipeline completo: audio -> texto -> procesamiento -> audio."""

    def __init__(self, stt: STTProvider, tts: TTSProvider, processor: AudioProcessor):
        self.stt = stt
        self.tts = tts
        self.processor = processor

    async def process_voice_message(
        self, audio_data: bytes, format: AudioFormat
    ) -> dict:
        """Procesa un mensaje de voz completo."""
        # 1. Validar
        valid, msg = self.processor.validate_file(audio_data, format)
        if not valid:
            return {"success": False, "error": msg}

        # 2. Transcribir
        transcription = await self.stt.transcribe(audio_data, format)

        # 3. Generar respuesta de voz
        response_text = f"Entendido: {transcription.text}"
        synthesis = await self.tts.synthesize(response_text)

        return {
            "success": True,
            "transcription": transcription.text,
            "language": transcription.language,
            "response_text": response_text,
            "response_audio_size": len(synthesis.audio_bytes),
        }


# ---------------------------------------------------------------------------
# Tests — AudioProcessor
# ---------------------------------------------------------------------------

class TestAudioProcessor:

    def setup_method(self):
        self.processor = AudioProcessor()

    def test_validate_valid_file(self):
        data = b"\x00" * 1000
        valid, msg = self.processor.validate_file(data, AudioFormat.OGG)
        assert valid is True
        assert msg == "ok"

    def test_validate_empty_file(self):
        valid, msg = self.processor.validate_file(b"", AudioFormat.MP3)
        assert valid is False
        assert "vacío" in msg

    def test_validate_too_large(self):
        data = b"\x00" * (26 * 1024 * 1024)
        valid, msg = self.processor.validate_file(data, AudioFormat.WAV)
        assert valid is False
        assert "grande" in msg

    def test_estimate_duration_ogg(self):
        # 16000 bytes / (128000/8) = 1.0 second
        data = b"\x00" * 16000
        duration = self.processor.estimate_duration(data, AudioFormat.OGG)
        assert abs(duration - 1.0) < 0.01

    def test_estimate_duration_wav_shorter(self):
        """WAV tiene mayor bitrate, así que la duración estimada es menor."""
        data = b"\x00" * 16000
        dur_ogg = self.processor.estimate_duration(data, AudioFormat.OGG)
        dur_wav = self.processor.estimate_duration(data, AudioFormat.WAV)
        assert dur_wav < dur_ogg

    def test_all_formats_supported(self):
        data = b"\x00" * 100
        for fmt in AudioFormat:
            valid, _ = self.processor.validate_file(data, fmt)
            assert valid is True


# ---------------------------------------------------------------------------
# Tests — STTProvider
# ---------------------------------------------------------------------------

class TestSTTProvider:

    @pytest.mark.asyncio
    async def test_transcribe_returns_result(self):
        stt = STTProvider()
        result = await stt.transcribe(b"\x00" * 100, AudioFormat.OGG)
        assert isinstance(result, TranscriptionResult)
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_transcribe_empty_raises(self):
        stt = STTProvider()
        with pytest.raises(ValueError, match="No hay datos"):
            await stt.transcribe(b"", AudioFormat.OGG)

    @pytest.mark.asyncio
    async def test_transcribe_language(self):
        stt = STTProvider()
        result = await stt.transcribe(b"\x00" * 100, AudioFormat.MP3)
        assert result.language == "es"

    @pytest.mark.asyncio
    async def test_transcribe_confidence(self):
        stt = STTProvider()
        result = await stt.transcribe(b"\x00" * 100, AudioFormat.OGG)
        assert 0 < result.confidence <= 1.0

    def test_default_provider(self):
        stt = STTProvider()
        assert stt.provider == "openai"


# ---------------------------------------------------------------------------
# Tests — TTSProvider
# ---------------------------------------------------------------------------

class TestTTSProvider:

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio(self):
        tts = TTSProvider()
        result = await tts.synthesize("Hola mundo")
        assert isinstance(result, SynthesisResult)
        assert len(result.audio_bytes) > 0

    @pytest.mark.asyncio
    async def test_synthesize_empty_raises(self):
        tts = TTSProvider()
        with pytest.raises(ValueError, match="No hay texto"):
            await tts.synthesize("")

    @pytest.mark.asyncio
    async def test_synthesize_whitespace_raises(self):
        tts = TTSProvider()
        with pytest.raises(ValueError):
            await tts.synthesize("   ")

    @pytest.mark.asyncio
    async def test_synthesize_format_is_mp3(self):
        tts = TTSProvider()
        result = await tts.synthesize("Test")
        assert result.format == AudioFormat.MP3

    def test_set_valid_voice(self):
        tts = TTSProvider()
        tts.set_voice("nova")
        assert tts.voice == "nova"

    def test_set_invalid_voice_raises(self):
        tts = TTSProvider()
        with pytest.raises(ValueError, match="no disponible"):
            tts.set_voice("jarvis")

    def test_available_voices(self):
        assert "alloy" in TTSProvider.AVAILABLE_VOICES
        assert len(TTSProvider.AVAILABLE_VOICES) == 6

    def test_default_voice(self):
        tts = TTSProvider()
        assert tts.voice == "alloy"


# ---------------------------------------------------------------------------
# Tests — VoicePipeline
# ---------------------------------------------------------------------------

class TestVoicePipeline:

    def setup_method(self):
        self.stt = STTProvider()
        self.tts = TTSProvider()
        self.processor = AudioProcessor()
        self.pipeline = VoicePipeline(self.stt, self.tts, self.processor)

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        audio = b"\x00" * 1000
        result = await self.pipeline.process_voice_message(audio, AudioFormat.OGG)
        assert result["success"] is True
        assert "transcription" in result
        assert "response_text" in result
        assert result["response_audio_size"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_invalid_audio(self):
        result = await self.pipeline.process_voice_message(b"", AudioFormat.OGG)
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pipeline_too_large(self):
        big_audio = b"\x00" * (26 * 1024 * 1024)
        result = await self.pipeline.process_voice_message(big_audio, AudioFormat.MP3)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_pipeline_response_includes_transcription(self):
        audio = b"\x00" * 500
        result = await self.pipeline.process_voice_message(audio, AudioFormat.OGG)
        assert "Entendido:" in result["response_text"]

    @pytest.mark.asyncio
    async def test_pipeline_detects_language(self):
        audio = b"\x00" * 500
        result = await self.pipeline.process_voice_message(audio, AudioFormat.OGG)
        assert result["language"] == "es"

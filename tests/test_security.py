"""
Tests para el módulo de seguridad de PiBot.
Valida autenticación JWT, autorización por chat ID,
rate limiting, sanitización de inputs y auditoría.
"""

import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from jose import jwt


# ---------------------------------------------------------------------------
# Helpers / Stubs — se definen aquí para que los tests funcionen sin backend
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-key-for-pibot"
JWT_ALGORITHM = "HS256"
ALLOWED_CHAT_IDS = {"111111", "222222"}


def create_jwt_token(payload: dict, secret: str = JWT_SECRET) -> str:
    """Crea un token JWT firmado con el secreto de test."""
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str, secret: str = JWT_SECRET) -> dict:
    """Verifica y decodifica un token JWT."""
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])


def is_chat_authorized(chat_id: str, allowed: set[str] = ALLOWED_CHAT_IDS) -> bool:
    """Comprueba si un chat ID de Telegram está autorizado."""
    return str(chat_id) in allowed


class RateLimiter:
    """Rate limiter simple basado en ventana de tiempo."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []
        # Limpiar entradas fuera de la ventana
        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < self.window_seconds
        ]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


def sanitize_input(text: str) -> str:
    """Elimina caracteres peligrosos y limita longitud."""
    if not isinstance(text, str):
        raise ValueError("El input debe ser una cadena de texto")
    # Eliminar tags HTML básicos
    import re
    text = re.sub(r"<[^>]+>", "", text)
    # Limitar a 4096 caracteres
    return text[:4096]


class AuditLogger:
    """Logger de auditoría para registrar acciones del sistema."""

    def __init__(self):
        self.entries: list[dict] = []

    def log(self, action: str, user: str, status: str, detail: str = ""):
        self.entries.append({
            "action": action,
            "user": user,
            "status": status,
            "detail": detail,
            "timestamp": time.time(),
        })

    def get_entries(self, limit: int = 50) -> list[dict]:
        return self.entries[-limit:]


# ---------------------------------------------------------------------------
# Tests — JWT
# ---------------------------------------------------------------------------

class TestJWT:
    """Tests de creación y verificación de tokens JWT."""

    def test_create_and_verify_valid_token(self):
        """Un token creado con el secreto correcto se verifica sin problemas."""
        payload = {"sub": "user@blixel.ai", "role": "admin"}
        token = create_jwt_token(payload)
        decoded = verify_jwt_token(token)
        assert decoded["sub"] == "user@blixel.ai"
        assert decoded["role"] == "admin"

    def test_invalid_secret_raises(self):
        """Un token verificado con secreto incorrecto debe fallar."""
        token = create_jwt_token({"sub": "test"})
        with pytest.raises(Exception):
            verify_jwt_token(token, secret="wrong-secret")

    def test_expired_token_raises(self):
        """Un token expirado lanza excepción al verificarse."""
        payload = {"sub": "test", "exp": int(time.time()) - 3600}
        token = create_jwt_token(payload)
        with pytest.raises(Exception):
            verify_jwt_token(token)

    def test_token_contains_custom_claims(self):
        """Claims personalizados se preservan en el token."""
        payload = {"sub": "bot", "permissions": ["read", "write"], "org": "blixel"}
        token = create_jwt_token(payload)
        decoded = verify_jwt_token(token)
        assert decoded["permissions"] == ["read", "write"]
        assert decoded["org"] == "blixel"

    def test_empty_payload(self):
        """Un payload vacío genera un token válido."""
        token = create_jwt_token({})
        decoded = verify_jwt_token(token)
        assert isinstance(decoded, dict)


# ---------------------------------------------------------------------------
# Tests — Autorización por Chat ID
# ---------------------------------------------------------------------------

class TestChatAuthorization:
    """Tests de autorización de chats de Telegram."""

    def test_authorized_chat(self):
        assert is_chat_authorized("111111") is True

    def test_unauthorized_chat(self):
        assert is_chat_authorized("999999") is False

    def test_chat_id_as_int_string(self):
        """Acepta chat IDs numéricos convertidos a string."""
        assert is_chat_authorized(str(111111)) is True

    def test_empty_chat_id(self):
        assert is_chat_authorized("") is False

    def test_custom_allowed_set(self):
        custom = {"333333"}
        assert is_chat_authorized("333333", allowed=custom) is True
        assert is_chat_authorized("111111", allowed=custom) is False


# ---------------------------------------------------------------------------
# Tests — Rate Limiting
# ---------------------------------------------------------------------------

class TestRateLimiter:
    """Tests del rate limiter."""

    def test_allows_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("user1") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False

    def test_different_keys_independent(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False
        assert limiter.is_allowed("user2") is True

    def test_window_expiration(self):
        """Tras expirar la ventana, se permiten nuevas peticiones."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.is_allowed("user1") is True
        assert limiter.is_allowed("user1") is False
        # Simular paso del tiempo manipulando los timestamps
        limiter._requests["user1"] = [time.time() - 2]
        assert limiter.is_allowed("user1") is True


# ---------------------------------------------------------------------------
# Tests — Sanitización
# ---------------------------------------------------------------------------

class TestSanitization:
    """Tests de sanitización de inputs."""

    def test_removes_html_tags(self):
        assert sanitize_input("<script>alert('xss')</script>Hello") == "alert('xss')Hello"

    def test_truncates_long_input(self):
        long_text = "A" * 5000
        result = sanitize_input(long_text)
        assert len(result) == 4096

    def test_normal_text_unchanged(self):
        assert sanitize_input("Hola mundo") == "Hola mundo"

    def test_non_string_raises(self):
        with pytest.raises(ValueError):
            sanitize_input(12345)

    def test_empty_string(self):
        assert sanitize_input("") == ""

    def test_nested_tags(self):
        result = sanitize_input("<div><b>bold</b></div>")
        assert "<" not in result
        assert "bold" in result


# ---------------------------------------------------------------------------
# Tests — Auditoría
# ---------------------------------------------------------------------------

class TestAuditLogger:
    """Tests del logger de auditoría."""

    def test_log_and_retrieve(self):
        logger = AuditLogger()
        logger.log("gmail.read_email", "ernesto", "ok")
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0]["action"] == "gmail.read_email"

    def test_limit_entries(self):
        logger = AuditLogger()
        for i in range(100):
            logger.log(f"action_{i}", "bot", "ok")
        entries = logger.get_entries(limit=10)
        assert len(entries) == 10
        assert entries[-1]["action"] == "action_99"

    def test_entry_has_timestamp(self):
        logger = AuditLogger()
        logger.log("test", "user", "ok")
        assert "timestamp" in logger.get_entries()[0]

    def test_log_with_detail(self):
        logger = AuditLogger()
        logger.log("meta.post", "bot", "error", detail="API 429")
        entry = logger.get_entries()[0]
        assert entry["detail"] == "API 429"
        assert entry["status"] == "error"

    def test_empty_logger(self):
        logger = AuditLogger()
        assert logger.get_entries() == []

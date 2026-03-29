"""
Servicio de gestión de archivos para PiBot.
Subida, almacenamiento y procesamiento de archivos.
"""

import uuid
from pathlib import Path

import structlog

from memory.postgres import log_audit

logger = structlog.get_logger()

UPLOAD_DIR = Path("static/uploads")


def init_uploads() -> None:
    """Crea el directorio de uploads si no existe."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("uploads_dir_ready", path=str(UPLOAD_DIR))


async def save_file(content: bytes, filename: str, session_id: str = "api") -> dict:
    """
    Guarda un archivo subido y devuelve info del archivo.
    """
    ext = Path(filename).suffix or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / unique_name
    filepath.write_bytes(content)

    size = len(content)
    url = f"/static/uploads/{unique_name}"

    await log_audit("files", "upload", detail=f"{filename} ({size} bytes)", session_id=session_id)
    logger.info("file_saved", original=filename, stored=unique_name, size=size)

    return {
        "filename": filename,
        "stored_as": unique_name,
        "url": url,
        "size": size,
    }

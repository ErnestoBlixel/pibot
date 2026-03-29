"""
PiBot — Punto de entrada FastAPI.
Orquestador multi-agente autónomo para Blixel AI.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings

import logging

_LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        _LOG_LEVELS.get(settings.LOG_LEVEL.upper(), 20)
    ),
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from memory.postgres import init_pool, close_pool
    from memory.redis_client import init_redis, close_redis

    logger.info("startup", environment=settings.ENVIRONMENT)
    await init_pool()
    await init_redis()

    from services.files import init_uploads
    init_uploads()

    logger.info("startup_complete", msg="PostgreSQL y Redis conectados")

    bot_task = None
    if settings.ENVIRONMENT == "production":
        import asyncio
        from interfaces.telegram_bot import start_bot
        bot_task = asyncio.create_task(start_bot())
        logger.info("telegram_bot_started")

    yield

    if bot_task and not bot_task.done():
        bot_task.cancel()
    await close_pool()
    await close_redis()
    logger.info("shutdown_complete")


app = FastAPI(
    title="PiBot",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://blixel.ai",
        "https://www.blixel.ai",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import router
app.include_router(router)

from interfaces.websocket import websocket_endpoint
app.websocket("/ws")(websocket_endpoint)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/dashboard")
async def dashboard():
    return FileResponse(str(STATIC_DIR / "dashboard.html"))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )

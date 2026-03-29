"""
Interfaz WebSocket para PiBot.
Permite comunicación en tiempo real con el dashboard.
"""

import json
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from config import settings

logger = structlog.get_logger()

# Conexiones activas
_connections: list[WebSocket] = []


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Endpoint WebSocket para comunicación en tiempo real."""
    await websocket.accept()
    _connections.append(websocket)
    logger.info("ws_connected", total=len(_connections))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "JSON inválido"})
                continue

            # Verificar token
            token = message.get("token", "")
            if token != settings.AGENT_AUTH_TOKEN:
                await websocket.send_json({"error": "Token inválido"})
                continue

            text = message.get("text", "")
            session_id = message.get("session_id", "ws_default")

            if not text:
                await websocket.send_json({"error": "Texto vacío"})
                continue

            from orchestrator.graph import process_message
            result = await process_message(message=text, session_id=session_id, channel="websocket")
            await websocket.send_json({
                "response": result["text"],
                "agent_used": result.get("agent_used"),
            })

    except WebSocketDisconnect:
        _connections.remove(websocket)
        logger.info("ws_disconnected", total=len(_connections))


async def broadcast(message: dict) -> None:
    """Envía un mensaje a todas las conexiones WebSocket activas."""
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)

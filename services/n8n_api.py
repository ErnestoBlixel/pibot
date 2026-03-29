"""
Cliente de la API de n8n para PiBot.
Gestión de workflows, ejecuciones y credenciales.
"""

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


def _headers() -> dict:
    """Headers comunes para la API de n8n."""
    return {
        "Content-Type": "application/json",
        "X-N8N-API-KEY": settings.N8N_WEBHOOK_SECRET,
    }


def _url(path: str) -> str:
    """Construye la URL completa de la API de n8n."""
    base = settings.N8N_BASE_URL.rstrip("/")
    return f"{base}/api/v1{path}"


async def list_workflows(active_only: bool = False) -> list[dict]:
    """Lista todos los workflows de n8n."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_url("/workflows"), headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    workflows = data.get("data", [])
    if active_only:
        workflows = [w for w in workflows if w.get("active")]
    return workflows


async def get_workflow(workflow_id: str) -> dict:
    """Obtiene los detalles de un workflow."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_url(f"/workflows/{workflow_id}"), headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def create_workflow(name: str, nodes: list, connections: dict, active: bool = False) -> dict:
    """Crea un nuevo workflow en n8n."""
    body = {"name": name, "nodes": nodes, "connections": connections, "active": active}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url("/workflows"), headers=_headers(), json=body)
        resp.raise_for_status()
        return resp.json()


async def activate_workflow(workflow_id: str) -> dict:
    """Activa un workflow."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(_url(f"/workflows/{workflow_id}"), headers=_headers(), json={"active": True})
        resp.raise_for_status()
        return resp.json()


async def deactivate_workflow(workflow_id: str) -> dict:
    """Desactiva un workflow."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(_url(f"/workflows/{workflow_id}"), headers=_headers(), json={"active": False})
        resp.raise_for_status()
        return resp.json()


async def import_workflow(workflow_json: dict) -> dict:
    """Importa un workflow desde JSON."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_url("/workflows"), headers=_headers(), json=workflow_json)
        resp.raise_for_status()
        return resp.json()


async def list_executions(workflow_id: str | None = None, limit: int = 20) -> list[dict]:
    """Lista ejecuciones recientes."""
    params = {"limit": limit}
    if workflow_id:
        params["workflowId"] = workflow_id
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_url("/executions"), headers=_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", [])


async def list_credentials() -> list[dict]:
    """Lista las credenciales configuradas en n8n."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_url("/credentials"), headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", [])

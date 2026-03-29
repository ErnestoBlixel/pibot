"""
Endpoints de la API de PiBot.
POST /message, POST /confirm, GET /history, GET /audit, GET /health
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from config import settings

router = APIRouter()


class MessageRequest(BaseModel):
    text: str
    session_id: str
    channel: str = "api"


class MessageResponse(BaseModel):
    response: str
    agent_used: str | None = None
    voice_url: str | None = None


class ConfirmRequest(BaseModel):
    redis_key: str
    decision: str


class ConfirmResponse(BaseModel):
    status: str


async def verify_token(request: Request) -> None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    token = auth.removeprefix("Bearer ").strip()
    if token != settings.AGENT_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/message", response_model=MessageResponse, dependencies=[Depends(verify_token)])
async def post_message(body: MessageRequest):
    from orchestrator.graph import process_message
    result = await process_message(message=body.text, session_id=body.session_id, channel=body.channel)
    return MessageResponse(response=result.get("text", ""), agent_used=result.get("agent_used"), voice_url=result.get("voice_url"))


@router.post("/confirm", response_model=ConfirmResponse, dependencies=[Depends(verify_token)])
async def post_confirm(body: ConfirmRequest):
    from security.confirmation import resolve_confirmation
    result = await resolve_confirmation(body.redis_key, body.decision)
    return ConfirmResponse(status=result)


@router.get("/history/{session_id}", dependencies=[Depends(verify_token)])
async def get_history(session_id: str, limit: int = 20):
    from memory.postgres import get_history
    rows = await get_history(session_id, limit=limit)
    return {"session_id": session_id, "messages": rows}


@router.get("/audit", dependencies=[Depends(verify_token)])
async def get_audit(limit: int = 50, agent_name: str | None = None, status: str | None = None):
    from memory.postgres import get_audit
    rows = await get_audit(limit=limit, agent_name=agent_name, status=status)
    return {"entries": rows}


@router.get("/memory/search", dependencies=[Depends(verify_token)])
async def search_memory(query: str, limit: int = 5, source_type: str | None = None):
    from memory.embeddings import search
    results = await search(query, limit=limit, source_type=source_type)
    return {"query": query, "results": results}


@router.get("/alerts", dependencies=[Depends(verify_token)])
async def get_alerts(limit: int = 20, severity: str | None = None, status: str | None = None):
    from memory.postgres import _get_pool
    pool = _get_pool()
    conditions = []
    params = []
    idx = 1
    if severity:
        conditions.append(f"severity = ${idx}")
        params.append(severity)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = await pool.fetch(f"SELECT * FROM agent_alerts {where} ORDER BY created_at DESC LIMIT ${idx}", *params)
    return {"alerts": [dict(r) for r in rows]}


@router.post("/prompts/approve/{prompt_name}/{version}", dependencies=[Depends(verify_token)])
async def approve_prompt_endpoint(prompt_name: str, version: int):
    from services.meta_agent import approve_prompt
    ok = await approve_prompt(prompt_name, version)
    if not ok:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada o ya procesada")
    return {"status": "approved", "prompt": prompt_name, "version": version}


@router.post("/prompts/reject/{prompt_name}/{version}", dependencies=[Depends(verify_token)])
async def reject_prompt_endpoint(prompt_name: str, version: int):
    from services.meta_agent import reject_prompt
    ok = await reject_prompt(prompt_name, version)
    if not ok:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada o ya procesada")
    return {"status": "rejected", "prompt": prompt_name, "version": version}


@router.get("/prompts", dependencies=[Depends(verify_token)])
async def list_prompts():
    from memory.postgres import _get_pool
    pool = _get_pool()
    rows = await pool.fetch(
        "SELECT id, prompt_name, version, status, change_reason, approved_by, performance, created_at "
        "FROM agent_prompt_versions ORDER BY prompt_name, version DESC"
    )
    return {"prompts": [dict(r) for r in rows]}


@router.get("/skills", dependencies=[Depends(verify_token)])
async def list_skills_endpoint():
    try:
        import skills.experts
    except Exception:
        pass
    from skills.base import list_skills
    return {"skills": list_skills()}


@router.get("/n8n/workflows", dependencies=[Depends(verify_token)])
async def n8n_list_workflows(active_only: bool = False):
    from services.n8n_api import list_workflows
    return {"workflows": await list_workflows(active_only=active_only)}


@router.get("/n8n/workflows/{workflow_id}", dependencies=[Depends(verify_token)])
async def n8n_get_workflow(workflow_id: str):
    from services.n8n_api import get_workflow
    return await get_workflow(workflow_id)


@router.post("/n8n/workflows", dependencies=[Depends(verify_token)])
async def n8n_create_workflow(body: dict):
    from services.n8n_api import create_workflow
    return await create_workflow(name=body["name"], nodes=body.get("nodes", []), connections=body.get("connections", {}), active=body.get("active", False))


@router.post("/n8n/workflows/{workflow_id}/activate", dependencies=[Depends(verify_token)])
async def n8n_activate(workflow_id: str):
    from services.n8n_api import activate_workflow
    return await activate_workflow(workflow_id)


@router.post("/n8n/workflows/{workflow_id}/deactivate", dependencies=[Depends(verify_token)])
async def n8n_deactivate(workflow_id: str):
    from services.n8n_api import deactivate_workflow
    return await deactivate_workflow(workflow_id)


@router.post("/n8n/import", dependencies=[Depends(verify_token)])
async def n8n_import_workflow(body: dict):
    from services.n8n_api import import_workflow
    return await import_workflow(body)


@router.get("/n8n/executions", dependencies=[Depends(verify_token)])
async def n8n_list_executions(workflow_id: str | None = None, limit: int = 20):
    from services.n8n_api import list_executions
    return {"executions": await list_executions(workflow_id=workflow_id, limit=limit)}


@router.get("/n8n/credentials", dependencies=[Depends(verify_token)])
async def n8n_list_credentials():
    from services.n8n_api import list_credentials
    return {"credentials": await list_credentials()}


@router.post("/upload", dependencies=[Depends(verify_token)])
async def upload_file(request: Request):
    form = await request.form()
    file = form.get("file")
    session_id = form.get("session_id", "api")
    if not file:
        raise HTTPException(status_code=400, detail="No se recibió archivo")
    content = await file.read()
    filename = getattr(file, "filename", "archivo")
    from services.files import save_file
    return await save_file(content, filename, session_id=session_id)

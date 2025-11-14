from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any

from ..models.config import ApplicationCreate, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def list_applications(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await ApplicationCreate.get_all(user_id=user_id)


@router.post("")
async def create_application(payload: ApplicationCreate) -> Dict[str, Any]:
    if not payload.name or not payload.url:
        raise HTTPException(status_code=400, detail="name 和 url 为必填项")
    return await ApplicationCreate.create(payload)


@router.get("/{application_id}")
async def get_application(application_id: str) -> Dict[str, Any]:
    app = await ApplicationCreate.get_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application 不存在")
    return app


@router.put("/{application_id}")
async def update_application(application_id: str, payload: ApplicationUpdate) -> Dict[str, Any]:
    existing = await ApplicationCreate.get_by_id(application_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application 不存在")
    updated = await ApplicationUpdate.update(application_id, payload)
    return updated or existing


@router.delete("/{application_id}")
async def delete_application(application_id: str) -> Dict[str, Any]:
    existing = await ApplicationCreate.get_by_id(application_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Application 不存在")
    await ApplicationCreate.delete(application_id)
    return {"ok": True}
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import verify_api_key
from api.models import GroupIn, GroupOut, ToggleIn
from database.engine import async_session
from database import crud

router = APIRouter(prefix="/groups", tags=["Groups"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[GroupOut])
async def list_groups():
    async with async_session() as session:
        groups = await crud.get_active_groups(session)
    return [GroupOut.model_validate(g) for g in groups]


@router.post("", response_model=GroupOut, status_code=201)
async def add_group(body: GroupIn):
    async with async_session() as session:
        try:
            group = await crud.add_group(session, chat_id=body.chat_id, title=body.title)
        except Exception:
            raise HTTPException(400, "Group already exists or database error")
    return GroupOut.model_validate(group)


@router.delete("/{chat_id}")
async def remove_group(chat_id: int):
    async with async_session() as session:
        ok = await crud.remove_group(session, chat_id=chat_id)
    if not ok:
        raise HTTPException(404, "Group not found")
    return {"detail": "removed"}


@router.patch("/{chat_id}/toggle")
async def toggle_group(chat_id: int, body: ToggleIn):
    async with async_session() as session:
        ok = await crud.toggle_group(session, chat_id=chat_id, is_active=body.is_active)
    if not ok:
        raise HTTPException(404, "Group not found")
    return {"detail": "updated", "is_active": body.is_active}

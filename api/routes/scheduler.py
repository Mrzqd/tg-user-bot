from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import verify_api_key
from api.models import ScheduleIn, ScheduleOut, ScheduleUpdate, ToggleIn
from bot import scheduler as sched_service
from database.engine import async_session
from database import crud

router = APIRouter(prefix="/schedules", tags=["Scheduled Messages"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[ScheduleOut])
async def list_schedules():
    async with async_session() as session:
        items = await crud.get_all_schedules(session)
    return [ScheduleOut.model_validate(s) for s in items]


@router.post("", response_model=ScheduleOut, status_code=201)
async def add_schedule(body: ScheduleIn):
    if not body.cron_expr and not body.run_at:
        raise HTTPException(400, "Either cron_expr or run_at must be provided")
    async with async_session() as session:
        sched = await crud.add_schedule(
            session, chat_id=body.chat_id, text=body.text,
            cron_expr=body.cron_expr, run_at=body.run_at,
            delete_after=body.delete_after, topic_id=body.topic_id,
        )
    sched_service.add_job(sched)
    return ScheduleOut.model_validate(sched)


@router.put("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(schedule_id: int, body: ScheduleUpdate):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    sched_service.remove_job(schedule_id)
    async with async_session() as session:
        sched = await crud.update_schedule(session, schedule_id, **updates)
    if not sched:
        raise HTTPException(404, "Schedule not found")
    if sched.is_active:
        sched_service.add_job(sched)
    return ScheduleOut.model_validate(sched)


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    sched_service.remove_job(schedule_id)
    async with async_session() as session:
        ok = await crud.delete_schedule(session, schedule_id)
    if not ok:
        raise HTTPException(404, "Schedule not found")
    return {"detail": "deleted"}


@router.patch("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int, body: ToggleIn):
    async with async_session() as session:
        ok = await crud.toggle_schedule(session, schedule_id, body.is_active)
    if not ok:
        raise HTTPException(404, "Schedule not found")
    if body.is_active:
        async with async_session() as session:
            items = await crud.get_active_schedules(session)
            for s in items:
                if s.id == schedule_id:
                    sched_service.add_job(s)
                    break
    else:
        sched_service.remove_job(schedule_id)
    return {"detail": "updated", "is_active": body.is_active}

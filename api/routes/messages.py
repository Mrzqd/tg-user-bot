from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.deps import verify_api_key
from api.models import MessageIn, MessageLogOut
from bot.client import userbot
from database.engine import async_session
from database import crud

router = APIRouter(prefix="/messages", tags=["Messages"], dependencies=[Depends(verify_api_key)])


@router.post("/send")
async def send_message(body: MessageIn):
    msg_id = await userbot.send_message(body.chat_id, body.text, reply_to=body.reply_to)
    return {"detail": "sent", "message_id": msg_id}


@router.get("/logs", response_model=list[MessageLogOut])
async def get_logs(
    chat_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    async with async_session() as session:
        logs = await crud.get_message_logs(session, chat_id=chat_id, limit=limit, offset=offset)
    return [MessageLogOut.model_validate(l) for l in logs]

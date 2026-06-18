from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import verify_api_key
from api.models import (
    TelegramAuthStatusOut,
    TelegramPasswordIn,
    TelegramSendCodeIn,
    TelegramSignInIn,
    TelegramSignInOut,
)
from bot.client import userbot
from bot.runtime import start_runtime
from config import settings

router = APIRouter(prefix="/telegram-auth", tags=["Telegram Auth"], dependencies=[Depends(verify_api_key)])


@router.get("/status", response_model=TelegramAuthStatusOut)
async def telegram_auth_status():
    await userbot.connect()
    authorized = await userbot.client.is_user_authorized()
    if not authorized:
        return TelegramAuthStatusOut(
            connected=userbot.is_connected,
            authorized=False,
            phone=settings.tg_phone,
        )

    me = await userbot.client.get_me()
    return TelegramAuthStatusOut(
        connected=userbot.is_connected,
        authorized=True,
        user_id=me.id,
        username=me.username,
        first_name=me.first_name,
        phone=settings.tg_phone,
    )


@router.post("/send-code")
async def send_code(body: TelegramSendCodeIn):
    await userbot.send_login_code(body.phone.strip())
    return {"detail": "sent"}


@router.post("/sign-in", response_model=TelegramSignInOut)
async def sign_in(body: TelegramSignInIn):
    status = await userbot.sign_in_with_code(body.code.strip())
    if status == "authorized":
        await start_runtime()
    return TelegramSignInOut(status=status)


@router.post("/password", response_model=TelegramSignInOut)
async def sign_in_password(body: TelegramPasswordIn):
    await userbot.sign_in_with_password(body.password)
    await start_runtime()
    return TelegramSignInOut(status="authorized")

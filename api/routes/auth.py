from __future__ import annotations

import asyncio
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, Request as FastAPIRequest

from api.deps import create_access_token
from api.models import WebAuthConfigOut, WebLoginIn, WebLoginOut
from config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


def _verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    if not settings.turnstile_secret_key:
        return True
    if not token:
        return False

    data = {
        "secret": settings.turnstile_secret_key,
        "response": token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    req = Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
    return bool(body.get("success"))


@router.get("/config", response_model=WebAuthConfigOut)
async def get_auth_config():
    return WebAuthConfigOut(
        turnstile_site_key=settings.turnstile_site_key,
        turnstile_required=bool(settings.turnstile_secret_key),
    )


@router.post("/login", response_model=WebLoginOut)
async def login(body: WebLoginIn, request: FastAPIRequest):
    expected_password = settings.web_password or settings.api_secret_key
    if body.username != settings.web_username or body.password != expected_password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    remote_ip = request.client.host if request.client else None
    if not await asyncio.to_thread(_verify_turnstile, body.turnstile_token, remote_ip):
        raise HTTPException(status_code=403, detail="Turnstile 校验失败")

    token, expires_in = create_access_token(body.username)
    return WebLoginOut(
        access_token=token,
        expires_in=expires_in,
        turnstile_site_key=settings.turnstile_site_key,
    )

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


def _sign(payload: bytes) -> str:
    return hmac.new(settings.api_secret_key.encode(), payload, hashlib.sha256).hexdigest()


def create_access_token(username: str) -> tuple[str, int]:
    expires_in = max(settings.web_session_ttl_hours, 1) * 3600
    payload = {
        "sub": username,
        "exp": int(time.time()) + expires_in,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")
    signature = _sign(encoded.encode())
    return f"{encoded}.{signature}", expires_in


def verify_access_token(token: str) -> str | None:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(encoded.encode()), signature):
        return None

    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except Exception:
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload.get("sub")


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    if api_key and hmac.compare_digest(api_key, settings.api_secret_key):
        return "api-key"
    if credentials and credentials.scheme.lower() == "bearer":
        username = verify_access_token(credentials.credentials)
        if username:
            return username
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")

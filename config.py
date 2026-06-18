from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    tg_api_id: int
    tg_api_hash: str
    tg_session_name: str = "userbot"
    tg_phone: str = ""

    # Proxy
    tg_proxy_type: str = ""
    tg_proxy_host: str = ""
    tg_proxy_port: int = 0
    tg_proxy_user: str = ""
    tg_proxy_pass: str = ""

    # Admin
    admin_user_ids: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_secret_key: str = "change-me"
    web_username: str = "admin"
    web_password: str = ""
    web_session_ttl_hours: int = 24
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""

    # Database
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'userbot.db'}"

    # Command reply auto-delete (seconds, 0 = keep forever)
    cmd_delete_after: int = 0

    # Media downloads
    download_dir: str = str(BASE_DIR / "downloads")
    download_threads: int = 16
    download_part_size_kb: int = 512

    # Logging
    log_level: str = "INFO"
    log_file: str = str(BASE_DIR / "logs" / "userbot.log")

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, v: str) -> str:
        return v

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_user_ids:
            return set()
        return {int(uid.strip()) for uid in self.admin_user_ids.split(",") if uid.strip()}

    @property
    def proxy_dict(self) -> Optional[tuple]:
        """Build Telethon-compatible proxy tuple: (type, host, port, rdns, user, pass)."""
        if not self.tg_proxy_type or not self.tg_proxy_host:
            return None
        import socks
        proxy_type_map = {
            "socks5": socks.SOCKS5,
            "socks4": socks.SOCKS4,
            "http": socks.HTTP,
        }
        ptype = proxy_type_map.get(self.tg_proxy_type.lower())
        if ptype is None:
            return None
        return (
            ptype,
            self.tg_proxy_host,
            self.tg_proxy_port or 1080,
            True,
            self.tg_proxy_user or None,
            self.tg_proxy_pass or None,
        )

    @property
    def session_path(self) -> str:
        sessions_dir = BASE_DIR / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        return str(sessions_dir / self.tg_session_name)

    @property
    def download_path(self) -> Path:
        path = Path(self.download_dir).expanduser()
        if not path.is_absolute():
            path = BASE_DIR / path
        return path


settings = Settings()

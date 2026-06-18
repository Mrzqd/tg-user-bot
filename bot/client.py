from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger
from telethon import TelegramClient

from config import settings


class TelegramUserBot:
    """Singleton wrapper around Telethon TelegramClient."""

    _instance: Optional[TelegramUserBot] = None
    _client: Optional[TelegramClient] = None
    _started: bool = False

    def __new__(cls) -> TelegramUserBot:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> TelegramClient:
        if self._client is None:
            raise RuntimeError("Telegram client not initialized. Call init() first.")
        return self._client

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    async def init(self) -> None:
        if self._client is not None:
            return

        proxy = settings.proxy_dict
        if proxy:
            logger.info(
                "Using proxy {}://{}:{}",
                settings.tg_proxy_type, settings.tg_proxy_host, settings.tg_proxy_port,
            )

        self._client = TelegramClient(
            settings.session_path,
            settings.tg_api_id,
            settings.tg_api_hash,
            proxy=proxy,
            system_version="4.16.30-vxCUSTOM",
            device_model="Userbot",
            app_version="1.0.0",
            auto_reconnect=True,
            connection_retries=5,
        )
        logger.info("Telegram client created (session={})", settings.tg_session_name)

    async def start(self) -> None:
        if self._started:
            return
        await self.init()
        if settings.tg_phone:
            await self.client.start(phone=settings.tg_phone)
        else:
            await self.client.start()
        me = await self.client.get_me()
        logger.info("Logged in as {} (id={})", me.first_name, me.id)
        self._started = True

    async def stop(self) -> None:
        if self._client and self._started:
            await self._client.disconnect()
            self._started = False
            logger.info("Telegram client disconnected")

    async def send_message(
        self, chat_id: int, text: str,
        reply_to: int | None = None,
        topic_id: int = 0,
        delete_after: int | None = None,
    ) -> int:
        """Send a message. topic_id targets a forum topic (used as reply_to when reply_to is None)."""
        effective_reply = reply_to if reply_to else (topic_id or None)
        msg = await self.client.send_message(chat_id, text, reply_to=effective_reply)
        if delete_after and delete_after > 0:
            loop = asyncio.get_running_loop()
            loop.call_later(
                delete_after,
                lambda m=msg.id: loop.create_task(self._delete_message(chat_id, m, delete_after)),
            )
        return msg.id

    async def click_button(
        self, chat_id: int, msg_id: int, click_text: str = "",
    ) -> bool:
        """Click an inline button on a message.
        click_text can be:
          - a pure integer string like "0", "1" => click by flat index
          - text string => find button whose text contains the string
          - empty string => click first button
        Returns True on success.
        """
        try:
            msg = await self.client.get_messages(chat_id, ids=msg_id)
            if not msg or not msg.buttons:
                logger.warning("[ClickBtn] msg {} in {} has no buttons", msg_id, chat_id)
                return False

            flat_buttons = [btn for row in msg.buttons for btn in row]
            if not flat_buttons:
                logger.warning("[ClickBtn] msg {} in {} buttons empty", msg_id, chat_id)
                return False

            target = None
            if not click_text or click_text.strip() == "":
                target = flat_buttons[0]
            elif click_text.strip().isdigit():
                idx = int(click_text.strip())
                if 0 <= idx < len(flat_buttons):
                    target = flat_buttons[idx]
                else:
                    logger.warning("[ClickBtn] index {} out of range (total {})", idx, len(flat_buttons))
                    return False
            else:
                for btn in flat_buttons:
                    if click_text.strip() in (btn.text or ""):
                        target = btn
                        break
                if not target:
                    logger.warning("[ClickBtn] no button matching '{}' in msg {}", click_text, msg_id)
                    return False

            await target.click()
            logger.info("[ClickBtn] Clicked '{}' on msg {} in {}", target.text, msg_id, chat_id)
            return True
        except Exception as e:
            logger.error("[ClickBtn] Failed to click button on msg {} in {}: {}", msg_id, chat_id, e)
            return False

    async def _delete_message(self, chat_id: int, msg_id: int, delay: int) -> None:
        try:
            await self.client.delete_messages(chat_id, [msg_id])
            logger.debug("[AutoDelete] Deleted msg {} in chat {} (after {}s)", msg_id, chat_id, delay)
        except Exception as e:
            logger.warning("[AutoDelete] Failed to delete msg {} in {}: {}", msg_id, chat_id, e)

    async def get_me(self):
        return await self.client.get_me()


userbot = TelegramUserBot()

"""
Message monitoring handler.
Listens to new messages in monitored groups, logs them,
and triggers auto-reply rules (with condition evaluation,
capture-group substitution, template rendering, reply delay,
auto-delete, button clicking, and forum topic awareness).
"""
from __future__ import annotations

import asyncio
import re

from loguru import logger
from telethon import events

from bot.client import userbot
from bot.conditions import build_context, evaluate_condition, render_template
from bot.filters import match_keyword, substitute_reply
from database.engine import async_session
from database import crud


def _get_topic_id(event: events.NewMessage.Event) -> int:
    reply_to = getattr(event.message, "reply_to", None)
    if reply_to and getattr(reply_to, "forum_topic", False):
        return reply_to.reply_to_top_id or reply_to.reply_to_msg_id or 0
    return 0


def register_listener_handlers() -> None:
    client = userbot.client

    @client.on(events.NewMessage(incoming=True))
    async def on_new_message(event: events.NewMessage.Event):
        chat_id = event.chat_id
        sender = await event.get_sender()
        if sender is None:
            return

        sender_id = sender.id
        sender_name = getattr(sender, "first_name", "") or getattr(sender, "title", "")
        text = event.raw_text
        topic_id = _get_topic_id(event)

        async with async_session() as session:
            groups = await crud.get_active_groups(session)
            monitored_ids = {g.chat_id for g in groups}

            if chat_id not in monitored_ids:
                return

            await crud.log_message(
                session,
                chat_id=chat_id,
                sender_id=sender_id,
                sender_name=sender_name,
                text=text,
                message_id=event.id,
                topic_id=topic_id,
            )
            logger.debug(
                "[Monitor] chat={} topic={} sender={}({}) msg={}",
                chat_id, topic_id, sender_name, sender_id, text[:80] if text else "<media>",
            )

            rules = await crud.get_active_rules(session, chat_id=chat_id)
            for rule in rules:
                if rule.topic_id and rule.topic_id != topic_id:
                    continue
                match = match_keyword(text, rule)
                if not match:
                    continue
                ctx = build_context(
                    sender_id=sender_id,
                    sender_name=sender_name,
                    text=text or "",
                    chat_id=chat_id,
                    topic_id=topic_id,
                    has_buttons=bool(getattr(event.message, "buttons", None)),
                    match_obj=match if isinstance(match, re.Match) else None,
                )

                if rule.condition and not evaluate_condition(rule.condition, ctx):
                    logger.debug("[Condition] rule={} skipped (condition='{}')", rule.id, rule.condition)
                    continue
                reply_delay = rule.reply_delay if rule.reply_delay > 0 else 0
                action = rule.action or "reply"

                if action == "click_button":
                    raw_click = substitute_reply(rule.click_text or "", match)
                    click_text = render_template(raw_click, ctx)
                    logger.info(
                        "[ClickBtn] rule={} keyword='{}' -> chat={} msg={} btn='{}' (delay={}s)",
                        rule.id, rule.keyword, chat_id, event.id, click_text, reply_delay,
                    )
                    if reply_delay:
                        asyncio.get_running_loop().call_later(
                            reply_delay,
                            lambda ct=click_text, mid=event.id: asyncio.get_running_loop().create_task(
                                userbot.click_button(chat_id, mid, ct)
                            ),
                        )
                    else:
                        await userbot.click_button(chat_id, event.id, click_text)

                    if rule.reply_text:
                        raw_reply = substitute_reply(rule.reply_text, match)
                        reply = render_template(raw_reply, ctx)
                        if not reply.strip():
                            break
                        delete_after = rule.delete_after if rule.delete_after > 0 else None
                        reply_to = None if rule.no_quote else event.id
                        send_topic = topic_id if rule.no_quote else 0
                        send_delay = reply_delay + 1 if reply_delay else 0
                        if send_delay:
                            asyncio.get_running_loop().call_later(
                                send_delay,
                                lambda r=reply, da=delete_after, rt=reply_to, tid=send_topic: asyncio.get_running_loop().create_task(
                                    userbot.send_message(chat_id, r, reply_to=rt, topic_id=tid, delete_after=da)
                                ),
                            )
                        else:
                            await userbot.send_message(
                                chat_id, reply, reply_to=reply_to,
                                topic_id=send_topic, delete_after=delete_after,
                            )
                else:
                    raw_reply = substitute_reply(rule.reply_text, match)
                    reply = render_template(raw_reply, ctx)
                    if not reply.strip():
                        logger.debug("[Template] rule={} reply empty after rendering, skipping", rule.id)
                        break
                    delete_after = rule.delete_after if rule.delete_after > 0 else None
                    reply_to = None if rule.no_quote else event.id
                    send_topic = topic_id if rule.no_quote else 0
                    logger.info(
                        "[AutoReply] rule={} keyword='{}' -> chat={} topic={} reply='{}' (quote={}, delay={}s, del={}s)",
                        rule.id, rule.keyword, chat_id, topic_id, reply[:60],
                        not rule.no_quote, reply_delay, delete_after,
                    )
                    if reply_delay:
                        asyncio.get_running_loop().call_later(
                            reply_delay,
                            lambda r=reply, da=delete_after, rt=reply_to, tid=send_topic: asyncio.get_running_loop().create_task(
                                userbot.send_message(chat_id, r, reply_to=rt, topic_id=tid, delete_after=da)
                            ),
                        )
                    else:
                        await userbot.send_message(
                            chat_id, reply,
                            reply_to=reply_to,
                            topic_id=send_topic,
                            delete_after=delete_after,
                        )
                break

    logger.info("Listener handlers registered")

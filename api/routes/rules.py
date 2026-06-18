from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import verify_api_key
from api.models import RuleIn, RuleOut, RuleUpdate, ToggleIn
from database.engine import async_session
from database import crud

router = APIRouter(prefix="/rules", tags=["Keyword Rules"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=list[RuleOut])
async def list_rules():
    async with async_session() as session:
        rules = await crud.get_all_rules(session)
    return [RuleOut.model_validate(r) for r in rules]


@router.post("", response_model=RuleOut, status_code=201)
async def add_rule(body: RuleIn):
    async with async_session() as session:
        rule = await crud.add_rule(
            session, keyword=body.keyword, reply_text=body.reply_text,
            chat_id=body.chat_id, topic_id=body.topic_id,
            action=body.action, click_text=body.click_text,
            condition=body.condition, is_regex=body.is_regex,
            no_quote=body.no_quote, reply_delay=body.reply_delay,
            delete_after=body.delete_after,
        )
    return RuleOut.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: int, body: RuleUpdate):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    async with async_session() as session:
        rule = await crud.update_rule(session, rule_id, **updates)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return RuleOut.model_validate(rule)


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int):
    async with async_session() as session:
        ok = await crud.delete_rule(session, rule_id)
    if not ok:
        raise HTTPException(404, "Rule not found")
    return {"detail": "deleted"}


@router.patch("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, body: ToggleIn):
    async with async_session() as session:
        ok = await crud.toggle_rule(session, rule_id, body.is_active)
    if not ok:
        raise HTTPException(404, "Rule not found")
    return {"detail": "updated", "is_active": body.is_active}

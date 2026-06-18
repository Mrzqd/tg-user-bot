"""
Safe condition evaluator and template renderer for keyword rules.

== Condition syntax (rule.condition field) ==
  sender_id == 123456
  sender_name contains "张三"
  text contains "VIP" and sender_id != 0
  $1 == "是" or $1 == "好的"
  has_buttons
  not has_buttons
  msg_len > 50

Operators:
  ==  !=  >  <  >=  <=
  contains   not contains
  startswith   endswith
  in [val1, val2]   not in [val1, val2]
Logic:
  <cond> and <cond>
  <cond> or <cond>
  not <cond>

== Template syntax (in reply_text) ==
  {if $1 == "是"}同意{elif $1 == "否"}拒绝{else}未知{endif}
  普通文本{if has_buttons}(有按钮){endif}混合使用

Context variables:
  sender_id, sender_name, text, chat_id, topic_id,
  has_buttons, msg_len, $0, $1, $2 ...
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger


def build_context(
    sender_id: int, sender_name: str, text: str,
    chat_id: int, topic_id: int, has_buttons: bool,
    match_obj: re.Match | None = None,
) -> dict:
    ctx: dict[str, Any] = {
        "sender_id": sender_id,
        "sender_name": sender_name,
        "text": text or "",
        "chat_id": chat_id,
        "topic_id": topic_id,
        "has_buttons": has_buttons,
        "msg_len": len(text) if text else 0,
    }
    if match_obj:
        ctx["$0"] = match_obj.group(0)
        for i, g in enumerate(match_obj.groups(), start=1):
            ctx[f"${i}"] = g if g is not None else ""
    return ctx


# ── Value resolution ──────────────────────────────────────

def _resolve(name: str, ctx: dict) -> Any:
    name = name.strip()
    if name in ctx:
        return ctx[name]
    if name.startswith("$") and name[1:].isdigit():
        return ctx.get(name, "")
    return ""


def _parse_value(s: str) -> Any:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lstrip("-").isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        return s


def _to_num(v: Any) -> int | float | None:
    if isinstance(v, (int, float)):
        return v
    try:
        return int(v)
    except (ValueError, TypeError):
        pass
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── Atom evaluator ────────────────────────────────────────

_ATOM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'^(\$\d+|\w+)\s+not\s+contains\s+(.+)$'), "not_contains"),
    (re.compile(r'^(\$\d+|\w+)\s+contains\s+(.+)$'), "contains"),
    (re.compile(r'^(\$\d+|\w+)\s+not\s+in\s+\[(.+)]$'), "not_in"),
    (re.compile(r'^(\$\d+|\w+)\s+in\s+\[(.+)]$'), "in"),
    (re.compile(r'^(\$\d+|\w+)\s+startswith\s+(.+)$'), "startswith"),
    (re.compile(r'^(\$\d+|\w+)\s+endswith\s+(.+)$'), "endswith"),
    (re.compile(r'^(\$\d+|\w+)\s*>=\s*(.+)$'), "gte"),
    (re.compile(r'^(\$\d+|\w+)\s*<=\s*(.+)$'), "lte"),
    (re.compile(r'^(\$\d+|\w+)\s*!=\s*(.+)$'), "neq"),
    (re.compile(r'^(\$\d+|\w+)\s*==\s*(.+)$'), "eq"),
    (re.compile(r'^(\$\d+|\w+)\s*>\s*(.+)$'), "gt"),
    (re.compile(r'^(\$\d+|\w+)\s*<\s*(.+)$'), "lt"),
]


def _eval_atom(expr: str, ctx: dict) -> bool:
    expr = expr.strip()
    if not expr:
        return True

    if expr.startswith("not "):
        return not _eval_atom(expr[4:], ctx)

    if expr in ("has_buttons",):
        return bool(ctx.get(expr, False))

    for pattern, op in _ATOM_PATTERNS:
        m = pattern.match(expr)
        if not m:
            continue
        var = _resolve(m.group(1), ctx)
        raw = m.group(2).strip()

        if op == "contains":
            return str(_parse_value(raw)) in str(var)
        if op == "not_contains":
            return str(_parse_value(raw)) not in str(var)
        if op == "startswith":
            return str(var).startswith(str(_parse_value(raw)))
        if op == "endswith":
            return str(var).endswith(str(_parse_value(raw)))
        if op in ("in", "not_in"):
            items = [_parse_value(x.strip()) for x in raw.split(",")]
            vn = _to_num(var)
            if vn is not None:
                item_set = {_to_num(x) for x in items} - {None}
                found = vn in item_set
            else:
                found = str(var) in {str(x) for x in items}
            return found if op == "in" else not found

        val = _parse_value(raw)
        vn, cn = _to_num(var), _to_num(val)
        if vn is not None and cn is not None:
            if op == "eq":  return vn == cn
            if op == "neq": return vn != cn
            if op == "gt":  return vn > cn
            if op == "lt":  return vn < cn
            if op == "gte": return vn >= cn
            if op == "lte": return vn <= cn

        vs, cs = str(var), str(val)
        if op == "eq":  return vs == cs
        if op == "neq": return vs != cs
        return False

    return False


# ── Logic splitter (respects quoted strings) ──────────────

def _split_logic(s: str) -> list[tuple[str, str | None]]:
    """Split by ' and ' / ' or ' outside of quotes.
    Returns [(atom_expr, operator_after), ...] where last operator is None.
    """
    tokens: list[tuple[str, str | None]] = []
    buf: list[str] = []
    in_q: str | None = None
    i = 0
    while i < len(s):
        c = s[i]
        if c in ('"', "'") and in_q is None:
            in_q = c
            buf.append(c)
        elif c == in_q:
            in_q = None
            buf.append(c)
        elif in_q is None:
            rest = s[i:]
            if rest.startswith(" and "):
                tokens.append(("".join(buf).strip(), "and"))
                buf.clear()
                i += 5
                continue
            if rest.startswith(" or "):
                tokens.append(("".join(buf).strip(), "or"))
                buf.clear()
                i += 4
                continue
            buf.append(c)
        else:
            buf.append(c)
        i += 1
    if buf:
        tokens.append(("".join(buf).strip(), None))
    return tokens


# ── Public: evaluate_condition ────────────────────────────

def evaluate_condition(condition: str, ctx: dict) -> bool:
    condition = condition.strip()
    if not condition:
        return True
    try:
        tokens = _split_logic(condition)
        if not tokens:
            return True
        result = _eval_atom(tokens[0][0], ctx)
        for idx in range(len(tokens) - 1):
            op = tokens[idx][1]
            nxt = _eval_atom(tokens[idx + 1][0], ctx)
            if op == "and":
                result = result and nxt
            elif op == "or":
                result = result or nxt
        return result
    except Exception as e:
        logger.warning("[Condition] Failed to evaluate '{}': {}", condition, e)
        return True


# ── Public: render_template ───────────────────────────────

def render_template(template: str, ctx: dict) -> str:
    """Process {if COND}...{elif COND}...{else}...{endif} blocks."""
    if "{if " not in template:
        return template
    try:
        result: list[str] = []
        pos = 0
        while pos < len(template):
            start = template.find("{if ", pos)
            if start == -1:
                result.append(template[pos:])
                break
            result.append(template[pos:start])
            end = template.find("{endif}", start)
            if end == -1:
                result.append(template[start:])
                break
            block = template[start : end + 7]
            result.append(_eval_if_block(block, ctx))
            pos = end + 7
        return "".join(result)
    except Exception as e:
        logger.warning("[Template] Failed to render '{}': {}", template[:80], e)
        return template


def _eval_if_block(block: str, ctx: dict) -> str:
    s = block[4:-7]  # strip '{if ' and '{endif}'
    brace = s.find("}")
    if brace == -1:
        return ""
    first_cond = s[:brace].strip()
    rest = s[brace + 1:]

    branches: list[tuple[str | None, str]] = []

    while True:
        elif_pos = rest.find("{elif ")
        else_pos = rest.find("{else}")
        if elif_pos == -1:
            elif_pos = len(rest)
        if else_pos == -1:
            else_pos = len(rest)

        next_pos = min(elif_pos, else_pos)
        branches.append((first_cond, rest[:next_pos]))

        if next_pos >= len(rest):
            break

        if rest[next_pos:].startswith("{elif "):
            rest = rest[next_pos + 6:]
            brace = rest.find("}")
            if brace == -1:
                break
            first_cond = rest[:brace].strip()
            rest = rest[brace + 1:]
        elif rest[next_pos:].startswith("{else}"):
            branches.append((None, rest[next_pos + 6:]))
            break

    for cond, body in branches:
        if cond is None or evaluate_condition(cond, ctx):
            return body
    return ""

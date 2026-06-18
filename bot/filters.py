from __future__ import annotations

import re
from typing import Match

from loguru import logger

from database.models import KeywordRule


def match_keyword(text: str, rule: KeywordRule) -> Match | bool:
    """Check whether *text* matches the given keyword rule.

    For regex rules, returns the re.Match object so callers can use
    capture groups for reply substitution ($1, $2, ...).
    For plain keyword rules, returns True/False.
    """
    if not text:
        return False
    try:
        if rule.is_regex:
            m = re.search(rule.keyword, text, re.IGNORECASE | re.DOTALL)
            return m if m else False
        return rule.keyword.lower() in text.lower()
    except re.error:
        logger.warning("Invalid regex in rule {}: {}", rule.id, rule.keyword)
        return False


def substitute_reply(reply_text: str, match: Match | bool) -> str:
    """Replace $0, $1, $2, ... in reply_text with match groups.
    $0 = full match, $1 = first capture group, etc.
    """
    if not isinstance(match, re.Match):
        return reply_text
    result = reply_text.replace("$0", match.group(0))
    for i, g in enumerate(match.groups(), start=1):
        result = result.replace(f"${i}", g if g is not None else "")
    return result

"""Helpers for finding notes and amounts in Gemini noter_v5b JSON output."""
import re
from typing import Optional


def get_note(data: dict, *patterns: str) -> Optional[dict]:
    """Find the note whose title matches any of the given regex patterns.
    When multiple notes match, return the one with the most raw_amounts entries."""
    matches = []
    for n in data.get("noter", []):
        title = (n.get("tittel") or "").lower()
        for pat in patterns:
            if re.search(pat, title, re.IGNORECASE):
                matches.append(n)
                break
    if not matches:
        return None
    matches.sort(key=lambda n: -len(n.get("raw_amounts", {})))
    return matches[0]


def get_amount(note: Optional[dict], *patterns: str):
    """Find the first amount whose key matches any of the regex patterns."""
    if not note:
        return None
    for k, v in note.get("raw_amounts", {}).items():
        for pat in patterns:
            if re.search(pat, k, re.IGNORECASE):
                return v
    return None


def all_amounts_matching(note: Optional[dict], *patterns: str) -> list[tuple[str, object]]:
    """Return all (key, value) pairs whose key matches any pattern."""
    if not note:
        return []
    out = []
    for k, v in note.get("raw_amounts", {}).items():
        for pat in patterns:
            if re.search(pat, k, re.IGNORECASE):
                out.append((k, v))
                break
    return out

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
    """Find the first amount whose key matches one of the regex patterns.

    Patterns are tried in order. For each pattern, ALL keys are checked; if
    multiple keys match the same pattern, the first dict-order key wins.
    Specifying patterns most-specific-first ensures e.g. that a year-specific
    pattern wins over a year-agnostic catchall."""
    if not note:
        return None
    amounts = note.get("raw_amounts", {})
    for pat in patterns:
        rgx = re.compile(pat, re.IGNORECASE)
        for k, v in amounts.items():
            if rgx.search(k):
                return v
    return None


def first_not_none(*values):
    """Return the first non-None value. Use when 0 is a valid extracted value
    that should not fall through to a fallback (Python's `or` is falsy on 0)."""
    for v in values:
        if v is not None:
            return v
    return None


def get_amount_with_fallback(
    note: Optional[dict],
    *regex_patterns: str,
    table: Optional[str] = None,
    field: Optional[str] = None,
    year: Optional[int] = None,
):
    """get_amount + schema_mapper fallback.

    Try regex patterns first (deterministic). If they all miss AND a
    canonical (table, field) is provided, fall back to fuzzy/embedding
    match against canonical synonyms.
    """
    val = get_amount(note, *regex_patterns)
    if val is not None:
        return val
    if note is None or table is None or field is None:
        return None
    from .schema_mapper import find_in_amounts
    return find_in_amounts(note.get("raw_amounts", {}), table, field, year=year)


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

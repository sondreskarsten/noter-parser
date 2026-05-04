"""Daglig leder + styre godtgjørelse. Can be in:
  - Lønnskostnad note (combined, EPAX-style)
  - "Godtgjørelse til ledende personer" standalone
  - "Lån og sikkerhetsstillelse til ledende personer" standalone
  - "Ytelser til daglig leder" sub-table
"""
import re
from ..matchers import get_amount


def _find_dl_note(data: dict):
    """Pick the note with most daglig-leder-related signal."""
    candidates = []
    for n in data.get("noter", []):
        text = (n.get("raw_text") or "").lower()
        title = (n.get("tittel") or "").lower()
        score = 0
        if "daglig leder" in text:
            score += 2
        if "ledende personer" in title or "ledende personer" in text:
            score += 2
        if any("daglig leder" in (k or "").lower() for k in n.get("raw_amounts", {}).keys()):
            score += 3
        if "godtgjørels" in title:
            score += 2
        if score:
            candidates.append((n, score))
    candidates.sort(key=lambda c: -c[1])
    return candidates[0][0] if candidates else None


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = _find_dl_note(data)
    if not note:
        return []
    text = note.get("raw_text", "") or ""
    name_match = re.search(
        r"[Dd]aglig leder\s+([A-ZÆØÅ][\w\s\-]+?)\s+(?:har|mottatt|i \d{4})",
        text,
    )
    name = name_match.group(1).strip() if name_match else "Daglig leder"
    lonn = get_amount(
        note,
        r"[Dd]aglig leder.*[Ll]ønn(?!sregulering)",
        r"[Yy]telser til.*[Dd]aglig leder.*[Ll]ønn",
        r"^[Dd]aglig leder lønn$",
        r"^Lønn til daglig leder$",
    )
    bonus = get_amount(note, r"[Dd]aglig leder.*[Bb]onus", r"^Bonus$")
    annen = get_amount(
        note,
        r"[Dd]aglig leder.*[Aa]nnen godtgjørelse",
        r"^[Aa]nnen godtgjørelse$",
    )
    if lonn is None and annen is None and bonus is None:
        return []
    if isinstance(lonn, (int, float)) and isinstance(bonus, (int, float)):
        lonn_total = lonn + bonus
    elif isinstance(lonn, (int, float)):
        lonn_total = lonn
    else:
        lonn_total = bonus
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "role": f"Daglig leder ({name})",
        "lonn_bonuser": lonn_total,
        "annen_godtgjorelse": annen,
    }]

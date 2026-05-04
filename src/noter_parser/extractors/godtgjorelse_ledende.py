import re
from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"lønnskostnad", r"lønninger", r"godtgjørels")
    if not note:
        return []
    text = note.get("raw_text", "") or ""
    if "daglig leder" not in text.lower() and not get_amount(note, r"[Dd]aglig leder"):
        return []
    name_match = re.search(r"[Dd]aglig leder\s+([A-ZÆØÅ][\w\s]+?)\s+(?:har|mottatt|i \d{4})", text)
    name = name_match.group(1).strip() if name_match else "Daglig leder"
    lonn = get_amount(
        note,
        r"[Dd]aglig leder.*[Ll]ønn(?!sregulering)",
        r"[Yy]telser til ledende.*[Ll]ønn",
        r"^[Dd]aglig leder lønn$",
    )
    bonus = get_amount(note, r"bonus")
    annen = get_amount(note, r"[Aa]nnen godtgjørelse")
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

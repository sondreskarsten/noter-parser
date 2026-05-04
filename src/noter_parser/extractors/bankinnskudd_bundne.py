import re
from ..matchers import get_note, get_amount, get_amount_with_fallback


def _from_text(text: str) -> int | None:
    """Extract bundne skattetrekksmidler from prose like
    'kr 2 910 050' or 'NOK 2,910,050'."""
    if not text:
        return None
    m = re.search(
        r"(?:kr|NOK)\.?\s+([\d\s.,]{4,})",
        text,
    )
    if not m:
        return None
    raw = re.sub(r"[\s.,]", "", m.group(1))
    if raw.isdigit():
        return int(raw)
    return None


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(
        data,
        r"^bankinnskudd$",
        r"bankinnskudd.*kontanter",
        r"^bankinnskudd,? kontanter",
    )
    if not note:
        return []
    amt = get_amount(
        note,
        rf"[Bb]undne skattetrekksmidler {year}",
        r"[Bb]undne skattetrekksmidler",
        r"[Ss]kattetrekksmidler",
        r"[Bb]undne midler",
    )
    if amt is None:
        amt = get_amount_with_fallback(
            note, table="bankinnskudd_bundne",
            field="bundne_skattetrekksmidler", year=year,
        )
    if amt is None:
        amt = _from_text(note.get("raw_text", "") or "")
    if amt is None:
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "bundne_skattetrekksmidler": amt,
    }]

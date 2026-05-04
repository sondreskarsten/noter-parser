import re
from ..matchers import get_note


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"andre forhold", r"andre saker", r"rettssak", r"erstatning")
    if not note:
        return []
    text = note.get("raw_text", "") or ""
    if "rettssak" not in text.lower() and "dom" not in text.lower() and "tvist" not in text.lower():
        return []
    m_amt = re.search(r"(\d{1,4})\s*million(?:er)?\s*kr", text, re.IGNORECASE)
    amount = int(m_amt.group(1)) * 1_000_000 if m_amt else None
    m_court = re.search(r"(tingretten|lagmannsretten|høyesterett)", text, re.IGNORECASE)
    court = m_court.group(1).capitalize() if m_court else None
    appealed = "anket" in text.lower()
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "court": court,
        "amount_nok": amount,
        "appealed": appealed,
        "narrative": text[:600],
    }]

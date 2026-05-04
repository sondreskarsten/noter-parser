import re
from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    amt = None
    note_afk = get_note(data, r"andre kortsiktige fordringer")
    if note_afk:
        amt = get_amount(
            note_afk,
            rf"[Ff]ordring [Ss]katte[Ff][Uu][Nn][Nn].*{year}",
            r"[Ff]ordring [Ss]katte[Ff][Uu][Nn][Nn]",
        )
    if amt is None:
        note_sf = get_note(data, r"^skattefunn$", r"skatte\s*funn")
        if note_sf:
            amt = get_amount(
                note_sf,
                rf"[Ff]orventet.*tilskudd.*{year}",
                r"[Ff]orventet.*tilskudd",
                r"[Tt]ilskudd",
            )
            if amt is None:
                text = note_sf.get("raw_text", "") or ""
                m = re.search(r"NOK\s+([\d\s]{4,})", text)
                if m:
                    amt = int(re.sub(r"\s+", "", m.group(1)))
    if amt is None:
        note_sk = get_note(data, r"^skattekostnad$")
        if note_sk:
            raw = get_amount(note_sk, rf"[Ss]kattefunn {year}", r"[Ss]kattefunn")
            if isinstance(raw, (int, float)):
                amt = abs(raw)
    if amt is None:
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "forventet_tilskudd_nok": abs(amt) if isinstance(amt, (int, float)) else amt,
    }]

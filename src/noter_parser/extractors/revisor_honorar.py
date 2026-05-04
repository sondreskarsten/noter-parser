"""Revisor honorar can appear in:
  - Lønnskostnad note (combined, like EPAX 2017-2024)
  - Standalone "Honorar til revisor" note
  - "Godtgjørelser" note

Scan all notes; pick the one with most revisor-related amounts."""
from ..matchers import get_amount, get_amount_with_fallback, first_not_none


def _score_note(note: dict) -> int:
    keys = note.get("raw_amounts", {}).keys()
    score = 0
    for k in keys:
        kl = k.lower()
        if "revisjon" in kl or "revisor" in kl or "attestasjon" in kl:
            score += 1
        if "skatterådgivning" in kl or "skatteradgivning" in kl:
            score += 1
    return score


def _find_revisor_note(data: dict):
    candidates = [(n, _score_note(n)) for n in data.get("noter", [])]
    candidates = [c for c in candidates if c[1] > 0]
    if not candidates:
        return None
    candidates.sort(key=lambda c: -c[1])
    return candidates[0][0]


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = _find_revisor_note(data)
    if not note:
        return []
    rev = first_not_none(
        get_amount(note, rf"[Ll]ovpålagt revisjon.*{year}", rf"^Lovpålagt revisjon$"),
        get_amount(
            note,
            r"[Ll]ovpålagt revisjon",
            r"^Revisjon$",
            r"[Hh]onorar.*revisjon",
            r"[Rr]evisjonshonorar",
        ),
        get_amount_with_fallback(note, table="revisor_honorar", field="revisjon", year=year),
    )
    rad = first_not_none(
        get_amount(
            note,
            rf"[Ss]katterådgivning.*{year}",
            rf"[Tt]eknisk bistand skatt.*{year}",
        ),
        get_amount(note, r"[Ss]katterådgivning", r"[Tt]eknisk bistand skatt"),
        get_amount_with_fallback(note, table="revisor_honorar", field="skatteradgivning", year=year),
    )
    annen = first_not_none(
        get_amount(note, rf"[Aa]ndre attestasjon.*{year}"),
        get_amount(
            note,
            r"[Aa]ndre attestasjon",
            r"[Aa]nnen bistand",
            r"[Aa]ndre tjenester",
        ),
        get_amount_with_fallback(note, table="revisor_honorar", field="annen_bistand", year=year),
    )
    sumk = first_not_none(
        get_amount(note, rf"^Sum honorar.*{year}$", rf"^Sum revisor.*{year}$"),
        get_amount(note, r"^Sum honorar.*$", r"^Sum revisor.*$"),
        get_amount_with_fallback(note, table="revisor_honorar", field="sum", year=year),
    )
    if rev is None and rad is None and annen is None:
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "revisjon": rev,
        "skatteradgivning": rad,
        "annen_bistand": annen,
        "sum": sumk,
    }]

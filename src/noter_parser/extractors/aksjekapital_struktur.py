from ..matchers import get_note, get_amount, get_amount_with_fallback, first_not_none
from ..config import NA


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(
        data,
        r"aksjekapital.*aksjonær",
        r"aksjekapital og aksjon",
        r"^aksjonærer$",
        r"^aksjekapital$",
    )
    if not note:
        return []
    antall = first_not_none(
        get_amount(
            note,
            r"^Ordinære aksjer Antall$",
            r"^Antall aksjer$",
            r"Ordinære aksjer.*Antall",
            r"^Sum Antall$",
            r"^Sum$",
        ),
        get_amount_with_fallback(note, table="aksjekapital_struktur", field="antall_aksjer", year=year),
    )
    if antall is None:
        return []
    palydende = first_not_none(
        get_amount(note, r"^Ordinære aksjer Pålydende$", r"Pålydende$"),
        get_amount_with_fallback(note, table="aksjekapital_struktur", field="palydende", year=year),
    )
    bokfort = first_not_none(
        get_amount(note, r"^Ordinære aksjer Bokført$", r"Bokført$", r"^Sum Bokført$"),
        get_amount_with_fallback(note, table="aksjekapital_struktur", field="bokfort_verdi", year=year),
    )
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "aksjeklasse": "Ordinære aksjer",
        "antall_aksjer": antall,
        "palydende": palydende,
        "bokfort_verdi": bokfort,
    }]

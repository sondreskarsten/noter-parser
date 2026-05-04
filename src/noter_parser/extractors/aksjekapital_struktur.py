from ..matchers import get_note, get_amount
from ..config import NA


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"aksjekapital.*aksjonær", r"aksjekapital og aksjon")
    if not note:
        return []
    antall = get_amount(
        note,
        r"^Ordinære aksjer Antall$",
        r"^Antall aksjer$",
        r"Ordinære aksjer.*Antall",
        r"^Sum Antall$",
        r"^Sum$",
    )
    if antall is None:
        return []
    palydende = get_amount(note, r"^Ordinære aksjer Pålydende$", r"Pålydende$")
    bokfort = get_amount(note, r"^Ordinære aksjer Bokført$", r"Bokført$", r"^Sum Bokført$")
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "aksjeklasse": "Ordinære aksjer",
        "antall_aksjer": antall,
        "palydende": palydende,
        "bokfort_verdi": bokfort,
    }]

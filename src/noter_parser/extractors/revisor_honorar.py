from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"lønnskostnad", r"godtgjørels", r"revisor")
    if not note:
        return []
    rev = (
        get_amount(note, rf"[Ll]ovpålagt revisjon.*{year}", rf"^Lovpålagt revisjon$")
        or get_amount(note, r"[Ll]ovpålagt revisjon")
    )
    rad = (
        get_amount(
            note,
            rf"[Ss]katterådgivning.*{year}",
            rf"[Tt]eknisk bistand skatt.*{year}",
        )
        or get_amount(note, r"[Ss]katterådgivning", r"[Tt]eknisk bistand skatt")
    )
    annen = (
        get_amount(note, rf"[Aa]ndre attestasjon.*{year}")
        or get_amount(note, r"[Aa]ndre attestasjon")
    )
    sumk = (
        get_amount(note, rf"^Sum honorar.*{year}$")
        or get_amount(note, r"^Sum honorar.*$")
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

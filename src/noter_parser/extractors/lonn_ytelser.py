from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"lønnskostnad", r"lønninger")
    if not note:
        return []
    lonn = (
        get_amount(note, rf"^Lønninger {year}$", rf"^Lønn {year}$")
        or get_amount(note, r"^Lønninger$", r"^Lønn$")
    )
    agavg = (
        get_amount(note, rf"^Arbeidsgiveravgift {year}$", rf"^Folketrygdavgift {year}$")
        or get_amount(note, r"^Arbeidsgiveravgift$", r"^Folketrygdavgift$")
    )
    pensjon = (
        get_amount(
            note,
            rf"^Pensjonskostnader? {year}$",
            rf"^Pensjonskostnader eks\. aga.*{year}$",
        )
        or get_amount(
            note,
            r"^Pensjonskostnader? eks\. aga.*$",
            r"^Pensjonskostnad(er)?$",
        )
    )
    andre = get_amount(note, rf"^Andre ytelser {year}$") or get_amount(note, r"^Andre ytelser$")
    sumk = (
        get_amount(
            note,
            rf"^Sum lønnskostnad {year}$",
            rf"^Sum lønnskost {year}$",
            rf"^Sum lønnskostnader {year}$",
        )
        or get_amount(note, r"^Sum lønnskostnad$", r"^Sum lønnskostnader$")
    )
    if sumk is None:
        parts = [x for x in (lonn, agavg, pensjon, andre) if isinstance(x, (int, float))]
        if parts:
            sumk = sum(parts)
    arsverk = (
        get_amount(note, rf"årsverk.*{year}", rf"Antall årsverk.*{year}")
        or get_amount(note, r"^.*årsverk.*$")
    )
    if all(x is None for x in (lonn, agavg, pensjon, sumk, arsverk)):
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "lonninger": lonn,
        "arbeidsgiveravgift": agavg,
        "pensjonskostnader": pensjon,
        "andre_ytelser": andre,
        "sum_lonnskostnader": sumk,
        "arsverk": arsverk,
    }]

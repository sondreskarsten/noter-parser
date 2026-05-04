from ..matchers import get_note, get_amount, first_not_none, get_amount_with_fallback


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"lønnskostnad", r"lønninger")
    if not note:
        return []
    lonn = first_not_none(
        get_amount(note, rf"^Lønninger {year}$", rf"^Lønn {year}$"),
        get_amount(note, r"^Lønninger$", r"^Lønn$"),
        get_amount_with_fallback(note, table="lonn_ytelser", field="lonninger", year=year),
    )
    agavg = first_not_none(
        get_amount(note, rf"^Arbeidsgiveravgift {year}$", rf"^Folketrygdavgift {year}$"),
        get_amount(note, r"^Arbeidsgiveravgift$", r"^Folketrygdavgift$"),
        get_amount_with_fallback(note, table="lonn_ytelser", field="arbeidsgiveravgift", year=year),
    )
    pensjon = first_not_none(
        get_amount(
            note,
            rf"^Pensjonskostnader? {year}$",
            rf"^Pensjonskostnader eks\. aga.*{year}$",
        ),
        get_amount(
            note,
            r"^Pensjonskostnader? eks\. aga.*$",
            r"^Pensjonskostnad(er)?$",
        ),
        get_amount_with_fallback(note, table="lonn_ytelser", field="pensjonskostnader", year=year),
    )
    andre = first_not_none(
        get_amount(note, rf"^Andre ytelser {year}$", rf"^Andre relaterte ytelser {year}$"),
        get_amount(note, r"^Andre ytelser$", r"^Andre relaterte ytelser$"),
        get_amount_with_fallback(note, table="lonn_ytelser", field="andre_ytelser", year=year),
    )
    sumk = first_not_none(
        get_amount(
            note,
            rf"^Sum lønnskostnad {year}$",
            rf"^Sum lønnskost {year}$",
            rf"^Sum lønnskostnader {year}$",
            rf"^Sum {year}$",
        ),
        get_amount(note, r"^Sum lønnskostnad$", r"^Sum lønnskostnader$"),
        get_amount_with_fallback(note, table="lonn_ytelser", field="sum_lonnskostnader", year=year),
    )
    if sumk is None:
        parts = [x for x in (lonn, agavg, pensjon, andre) if isinstance(x, (int, float))]
        if parts:
            sumk = sum(parts)
    arsverk = first_not_none(
        get_amount(note, rf"årsverk.*{year}", rf"Antall årsverk.*{year}"),
        get_amount(note, r"^.*årsverk.*$"),
        get_amount_with_fallback(note, table="lonn_ytelser", field="arsverk", year=year),
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

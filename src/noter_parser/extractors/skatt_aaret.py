from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"^skatt$", r"^skattekostnad$", r"skattekostn")
    if not note:
        return []
    rb = (
        get_amount(
            note,
            rf"^Resultat før skatt {year}$",
            rf"Årsresultat før skatt {year}",
            rf"Regnskapsmessig resultat før skatt(?:kostnad)? {year}",
            rf"Resultat før skatt(?:kostnad)? {year}",
        )
        or get_amount(note, r"Resultat før skatt$", r"Resultat før skattekostnad$")
    )
    bskatt = (
        get_amount(
            note,
            rf"^Betalbar skatt {year}$",
            rf"^Betalbar skatt på årets resultat {year}$",
        )
        or get_amount(note, r"^Betalbar skatt$")
    )
    e_us = (
        get_amount(
            note,
            rf"^Endring i utsatt skatt {year}$",
            rf"^Endring utsatt skatt {year}$",
        )
        or get_amount(note, r"^Endring i utsatt skatt$", r"^Endring utsatt skatt$")
    )
    skattek = (
        get_amount(
            note,
            rf"^Skattekostnad ordinært resultat {year}$",
            rf"^Skattekostnad i resultatregnskapet {year}$",
        )
        or get_amount(
            note,
            r"^Skattekostnad ordinært resultat$",
            r"^Skattekostnad i resultatregnskapet$",
        )
    )
    sptl = (
        get_amount(
            note,
            rf"^Skattepliktig inntekt {year}$",
            rf"^Skattepliktig inntekt \(grunnlag for betalbar skatt i balansen\) {year}$",
        )
        or get_amount(note, r"^Skattepliktig inntekt$")
    )
    kavgitt = (
        get_amount(
            note,
            rf"^Avgitt konsernbidrag {year}$",
            rf"^Mottatt/avgitt konsernbidrag.*{year}$",
        )
        or get_amount(
            note,
            r"^Avgitt konsernbidrag$",
            r"^Mottatt/avgitt konsernbidrag.*$",
        )
    )
    kmottatt = (
        get_amount(
            note,
            rf"^Mottatt konsernbidrag {year}$",
            rf"^Skatteeffekt mottatt konsernbidrag {year}$",
        )
        or get_amount(note, r"^Mottatt konsernbidrag$")
    )
    if all(x is None for x in (rb, bskatt, skattek, sptl)):
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "resultat_for_skatt": rb,
        "skattepliktig_inntekt": sptl,
        "betalbar_skatt": bskatt,
        "endring_utsatt_skatt": e_us,
        "skattekostnad_total": skattek,
        "konsernbidrag_avgitt_with_skatte_effect": kavgitt,
        "konsernbidrag_mottatt_with_skatte_effect": kmottatt,
    }]

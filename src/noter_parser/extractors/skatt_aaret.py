from ..matchers import get_note, get_amount, get_amount_with_fallback, first_not_none


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(
        data,
        r"^skatt$",
        r"^skattekostnad$",
        r"^SKATT$",
        r"skattekostn",
        r"spesifisering av skatt",
    )
    if not note:
        return []
    rb = first_not_none(
        get_amount(
            note,
            rf"^Resultat før skatt {year}$",
            rf"^Skattepliktig inntekt: Resultat før skatt {year}$",
            rf"Skattepliktig inntekt:? Resultat før skatt {year}",
            rf"Årsresultat før skatt {year}",
            rf"Regnskapsmessig resultat før skatt(?:kostnad)? {year}",
            rf"Resultat før skatt(?:kostnad)? {year}",
        ),
        get_amount(note, r"Resultat før skatt$", r"Resultat før skattekostnad$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="resultat_for_skatt", year=year),
    )
    bskatt = first_not_none(
        get_amount(
            note,
            rf"^Betalbar skatt {year}$",
            rf"^Betalbar skatt på årets resultat {year}$",
            rf"^Resultatført skatt.*?: Betalbar skatt {year}$",
            rf"Resultatført skatt.*?:? Betalbar skatt {year}",
            rf"Betalbar skatt i balansen:? Betalbar skatt på årets resultat {year}",
        ),
        get_amount(note, r"^Betalbar skatt$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="betalbar_skatt", year=year),
    )
    e_us = first_not_none(
        get_amount(
            note,
            rf"^Endring i utsatt skatt {year}$",
            rf"^Endring utsatt skatt {year}$",
            rf"Resultatført skatt.*?:? Endring i utsatt skatte?fordel? {year}",
            rf"Endring i utsatt skattefordel {year}",
        ),
        get_amount(note, r"^Endring i utsatt skatt$", r"^Endring utsatt skatt$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="endring_utsatt_skatt", year=year),
    )
    skattek = first_not_none(
        get_amount(
            note,
            rf"^Skattekostnad ordinært resultat {year}$",
            rf"^Skattekostnad i resultatregnskapet {year}$",
            rf"Resultatført skatt.*?:? Skattekostnad ordinært resultat {year}",
        ),
        get_amount(note, r"^Skattekostnad ordinært resultat$", r"^Skattekostnad i resultatregnskapet$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="skattekostnad_total", year=year),
    )
    sptl = first_not_none(
        get_amount(
            note,
            rf"^Skattepliktig inntekt {year}$",
            rf"^Skattepliktig inntekt: Skattepliktig inntekt {year}$",
            rf"Skattepliktig inntekt:? Skattepliktig inntekt {year}",
            rf"^Skattepliktig inntekt \(grunnlag for betalbar skatt i balansen\) {year}$",
        ),
        get_amount(note, r"^Skattepliktig inntekt$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="skattepliktig_inntekt", year=year),
    )
    kavgitt = first_not_none(
        get_amount(
            note,
            rf"^Avgitt konsernbidrag {year}$",
            rf"^Mottatt/avgitt konsernbidrag.*{year}$",
            rf"Skattepliktig inntekt:? Avgift konsernbidrag {year}",
            rf"Skattepliktig inntekt:? Avgitt konsernbidrag {year}",
        ),
        get_amount(note, r"^Avgitt konsernbidrag$", r"^Mottatt/avgitt konsernbidrag.*$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="konsernbidrag_avgitt_with_skatte_effect", year=year),
    )
    kmottatt = first_not_none(
        get_amount(
            note,
            rf"^Mottatt konsernbidrag {year}$",
            rf"^Skatteeffekt mottatt konsernbidrag {year}$",
            rf"Skattepliktig inntekt:? Mottatt konsernbidrag {year}",
        ),
        get_amount(note, r"^Mottatt konsernbidrag$"),
        get_amount_with_fallback(note, table="skatt_aaret", field="konsernbidrag_mottatt_with_skatte_effect", year=year),
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

from ..matchers import get_note, get_amount


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"^egenkapital$")
    if not note:
        return []
    yr2 = str(year)[-2:]
    yr4 = str(year)
    sum_ek = (
        get_amount(
            note,
            rf"31\.12\.{yr4}.*SUM",
            rf"31\.12\.{yr2}.*SUM",
            rf"31\.12\.{yr4}.*Sum",
            rf"31\.12\.{yr2}.*Sum",
        )
        or get_amount(
            note,
            rf"Egenkapital 31\.12\.{yr2}.*Sum",
            rf"Egenkapital pr\.? 31\.12\.{yr2}.*Sum",
            rf"Egenkapital 31\.12\.{yr4}.*Sum",
            rf"EK pr\.? 31\.12\.{yr4}.*Sum",
        )
    )
    aksjekap = get_amount(
        note,
        rf"31\.12\.{yr4}.*Aksjekapital",
        rf"31\.12\.{yr2}.*Aksjekapital",
        rf"31\.12\.{yr4}.*Aksje-?\s*kapital",
        rf"31\.12\.{yr2}.*Aksje-?\s*kapital",
    )
    innskutt = get_amount(
        note,
        rf"31\.12\.{yr4}.*Annen innskutt",
        rf"31\.12\.{yr2}.*Annen innskutt",
    )
    opptjent = get_amount(
        note,
        rf"31\.12\.{yr4}.*Annen opptjent",
        rf"31\.12\.{yr2}.*Annen opptjent",
        rf"31\.12\.{yr4}.*Annen egen-?\s*kapital",
        rf"31\.12\.{yr2}.*Annen egen-?\s*kapital",
        rf"31\.12\.{yr4}.*Annen egenkapital",
        rf"31\.12\.{yr2}.*Annen egenkapital",
    )
    kbidrag_mottatt = get_amount(
        note,
        r"[Mm]ottatt konsernbidrag.*SUM",
        r"[Mm]ottatt konsernbidrag.*Sum",
        r"[Kk]onsernbidrag mottatt",
    )
    kbidrag_avgitt = get_amount(
        note,
        r"[Aa]vgitt konsernbidrag.*SUM",
        r"[Aa]vgitt konsernbidrag.*Sum",
        r"Avsatt konsernbidrag",
        r"[Kk]onsernbidrag avgitt",
        r"[Kk]onsernbidrag avsatt",
    )
    if sum_ek is None and aksjekap is None:
        return []
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "sum_egenkapital": sum_ek,
        "aksjekapital": aksjekap,
        "annen_innskutt_ek": innskutt,
        "annen_opptjent_ek": opptjent,
        "konsernbidrag_mottatt_netto": kbidrag_mottatt,
        "konsernbidrag_avgitt_netto": kbidrag_avgitt,
        "egenkapital_negativ": (sum_ek is not None and isinstance(sum_ek, (int, float)) and sum_ek < 0),
    }]

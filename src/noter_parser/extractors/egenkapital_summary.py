from ..matchers import get_note, get_amount, get_amount_with_fallback


def _match_field(note, year, field_alts: list[str], table=None, canonical_field=None):
    """Find a value matching '<field> at end-of-year' across any of:
      - 'Egenkapital 31.12.YYYY ... <field>'
      - 'Pr. 31.12.YYYY <field>'
      - '<field> Pr. 31.12.YYYY' (reversed)
      - '<field> 31.12.YYYY'
      - 'Egenkapital pr. 31.12. <field>' (no year, period style — closing)
      - 'Egenkapital 31.12. <field>'

    With schema_mapper fallback if regex misses and canonical_field given.
    """
    yr2, yr4 = str(year)[-2:], str(year)
    field_pat = "(?:" + "|".join(field_alts) + ")"
    candidates = [
        rf"31\.12\.{yr4}.*{field_pat}",
        rf"31\.12\.{yr2}.*{field_pat}",
        rf"{field_pat}.*31\.12\.{yr4}",
        rf"{field_pat}.*31\.12\.{yr2}",
        rf"31\.12\..*{field_pat}",
    ]
    return get_amount_with_fallback(
        note, *candidates,
        table=table, field=canonical_field, year=year,
    )


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"^egenkapital$")
    if not note:
        return []
    sum_ek = _match_field(note, year, [
        r"Sum egenkapital", r"^SUM$", r"Sum$",
    ], table="egenkapital_summary", canonical_field="sum_egenkapital")
    aksjekap = _match_field(note, year, [
        r"Aksjekapital", r"Aksje-?\s*kapital",
    ], table="egenkapital_summary", canonical_field="aksjekapital")
    innskutt = _match_field(note, year, [
        r"Annen innskutt", r"Overkurs",
    ], table="egenkapital_summary", canonical_field="annen_innskutt_ek")
    opptjent = _match_field(note, year, [
        r"Annen opptjent",
        r"Annen egen-?\s*kapital",
        r"Annen egenkapital",
        r"Opptjent egenkapital",
        r"Annen EK",
    ], table="egenkapital_summary", canonical_field="annen_opptjent_ek")
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
        r"^- Avgitt konsernbidrag$",
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

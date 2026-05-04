from ..matchers import get_note, get_amount, get_amount_with_fallback, first_not_none


_ASSET_CLASSES = [
    ("Tomter", "Tomter"),
    ("Bygninger", r"Bygn(\.|ing)? og annen fast eiendom"),
    ("Maskiner og anlegg", "Maskiner og anlegg"),
    ("Driftsløsøre", r"Dr\.?løsøre|Driftsløsøre"),
    ("Anlegg under utførelse", r"Anlegg under (utførelse|oppførelse)"),
    ("SUM", r"^SUM$|^Sum$"),
]


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(
        data,
        r"varige driftsmidler",
        r"^anleggsmidler$",
        r"varige driftsmidler.*immaterielle",
    )
    if not note:
        return []
    rows = []
    for label, pat in _ASSET_CLASSES:
        ank01 = get_amount(note, rf"Anskaffelseskost\s*(pr\.?)?\s*0?1\.0?1.*{pat}")
        ank31 = get_amount(note, rf"Anskaffelseskost\s*(pr\.?)?\s*3?1\.12.*{pat}")
        tilgang = get_amount(note, rf"^Tilgang.*{pat}$")
        balanse = get_amount(
            note,
            rf"Bokført verdi\s*(pr\.?)?\s*3?1\.12.*{pat}",
            rf"Bokført verdi\s*3?1\.1?2\.{str(year)[-2:]}.*{pat}",
            rf"Balanseført verdi.*{pat}",
        )
        avskr = get_amount(note, rf"Årets avskrivninger.*{pat}")
        nedskr = get_amount(note, rf"Årets nedskrivninger.*{pat}")
        akk_av = get_amount(note, rf"Akk\.?\s*av(skrivninger)?.*3?1\.12.*{pat}")
        akk_nedskr = get_amount(
            note, rf"Akk\.?\s*nedskrivninger\s*(pr\.?)?\s*3?1\.12.*{pat}",
        )
        if all(x is None for x in (ank31, balanse, avskr, nedskr)):
            continue
        rows.append({
            "orgnr": orgnr,
            "report_year": year,
            "source_filing_year": year,
            "asset_class": label,
            "anskaffelseskost_01_01": ank01,
            "tilgang": tilgang,
            "anskaffelseskost_31_12": ank31,
            "akkumulerte_avskrivninger_31_12": akk_av,
            "akkumulerte_nedskrivninger_31_12": akk_nedskr,
            "balansefort_31_12": balanse,
            "arets_avskrivninger": avskr,
            "arets_nedskrivninger": nedskr,
        })
    if not rows:
        ank01 = first_not_none(
            get_amount(
                note,
                r"^Anskaffelseskost\s*(pr\.?)?\s*0?1\.0?1\.?\s*$",
                r"Anskaffelseskost\s*(pr\.?)?\s*0?1\.0?1\.",
            ),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="anskaffelseskost_01_01", year=year),
        )
        ank31 = first_not_none(
            get_amount(
                note,
                r"^Anskaffelseskost\s*(pr\.?)?\s*3?1\.12\.?\s*$",
                r"Anskaffelseskost\s*(pr\.?)?\s*3?1\.12\.",
            ),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="anskaffelseskost_31_12", year=year),
        )
        tilgang = first_not_none(
            get_amount(note, r"^Tilgang(\s+i året)?$", r"^Tilgang\s*$"),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="tilgang", year=year),
        )
        avgang = first_not_none(
            get_amount(note, r"^Avgang(\s+i året)?$", r"^Avgang\s*$"),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="avgang", year=year),
        )
        balanse = first_not_none(
            get_amount(
                note,
                r"^Bokført verdi.*3?1\.12\.?\s*$",
                r"^Balanseført verdi.*3?1\.12\.?\s*$",
                r"^Balanseført verdi per 3?1\.12\.?\s*$",
            ),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="balansefort_31_12", year=year),
        )
        avskr = first_not_none(
            get_amount(
                note,
                r"^Avskrivninger.*regnskapsåret",
                r"^Avskrivninger, nedskrivninger.*",
                r"^Årets avskrivninger\s*$",
            ),
            get_amount_with_fallback(note, table="anleggsmidler_rollforward", field="arets_avskrivninger", year=year),
        )
        if any(x is not None for x in (ank01, ank31, tilgang, balanse, avskr)):
            rows.append({
                "orgnr": orgnr,
                "report_year": year,
                "source_filing_year": year,
                "asset_class": "TOTAL",
                "anskaffelseskost_01_01": ank01,
                "tilgang": tilgang,
                "anskaffelseskost_31_12": ank31,
                "akkumulerte_avskrivninger_31_12": None,
                "akkumulerte_nedskrivninger_31_12": None,
                "balansefort_31_12": balanse,
                "arets_avskrivninger": avskr,
                "arets_nedskrivninger": None,
            })
    return rows

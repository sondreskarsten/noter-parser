from ..matchers import get_note, get_amount


_ASSET_CLASSES = [
    ("Tomter", "Tomter"),
    ("Bygninger", r"Bygn(\.|ing)? og annen fast eiendom"),
    ("Maskiner og anlegg", "Maskiner og anlegg"),
    ("Driftsløsøre", r"Dr\.?løsøre|Driftsløsøre"),
    ("Anlegg under utførelse", r"Anlegg under (utførelse|oppførelse)"),
    ("SUM", r"^SUM$|^Sum$"),
]


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"varige driftsmidler")
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
        )
        avskr = get_amount(note, rf"Årets avskrivninger.*{pat}")
        nedskr = get_amount(note, rf"Årets nedskrivninger.*{pat}")
        akk_av = get_amount(note, rf"Akk\.?\s*av(skrivninger)?.*3?1\.12.*{pat}")
        akk_nedskr = get_amount(note, rf"Akk\.?\s*nedskrivninger\s*(pr\.?)?\s*3?1\.12.*{pat}")
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
    return rows

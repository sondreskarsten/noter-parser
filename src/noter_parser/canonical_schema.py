"""Canonical schema for the 14 noter-parser output tables.

Each table maps to a list of canonical column labels with multilingual
synonyms. The schema-mapper uses these labels as targets when matching
raw_amounts keys via embedding similarity.

Synonym lists are populated from observed real Norwegian variants. Add new
synonyms here when you patch a parser to handle a new label form — keep
the parser regexes AND the canonical synonyms in sync.

References:
- IFRS Taxonomy concept QNames (e.g. ifrs-full:Goodwill)
- NRS / NGAAP standard line-item names
- Skatteetaten Næringslivskoder
"""

# Each entry: canonical_field -> list of Norwegian synonyms / OCR variants
CANONICAL_FIELDS: dict[str, dict[str, list[str]]] = {
    "egenkapital_summary": {
        "sum_egenkapital": [
            "Sum egenkapital", "SUM egenkapital", "Egenkapital totalt",
            "Sum EK", "Total egenkapital", "Egenkapital sum",
        ],
        "aksjekapital": [
            "Aksjekapital", "Aksje kapital", "Aksje-kapital",
            "Innskutt aksjekapital", "Pålydende aksjekapital",
        ],
        "annen_innskutt_ek": [
            "Annen innskutt egenkapital", "Overkurs", "Overkursfond",
            "Annen innskutt EK", "Innskutt egenkapital annen",
        ],
        "annen_opptjent_ek": [
            "Annen opptjent egenkapital", "Annen egenkapital",
            "Annen egen-kapital", "Annen EK", "Opptjent egenkapital",
            "Annen opptjent kapital",
        ],
        "konsernbidrag_mottatt_netto": [
            "Konsernbidrag mottatt", "Mottatt konsernbidrag",
            "Konsernbidrag mottatt netto etter skatt",
        ],
        "konsernbidrag_avgitt_netto": [
            "Konsernbidrag avgitt", "Avgitt konsernbidrag",
            "Avsatt konsernbidrag", "Konsernbidrag avsatt",
            "Avgitt konsernbidrag etter skatt",
        ],
    },

    "lonn_ytelser": {
        "lonninger": [
            "Lønninger", "Lønn", "Lønn og feriepenger", "Lønnskostnad",
        ],
        "arbeidsgiveravgift": [
            "Arbeidsgiveravgift", "Folketrygdavgift", "Arbeidsgiveravgift av lønn",
        ],
        "pensjonskostnader": [
            "Pensjonskostnader", "Pensjonskostnad", "Pensjon",
            "Pensjonskostnader eks aga", "Netto pensjonskostnad",
        ],
        "andre_ytelser": [
            "Andre ytelser", "Andre relaterte ytelser",
            "Andre personalkostnader", "Andre lønnskostnader",
        ],
        "sum_lonnskostnader": [
            "Sum lønnskostnad", "Sum lønnskostnader",
            "Sum lønnskost", "Totale lønnskostnader",
        ],
        "arsverk": [
            "Antall årsverk", "Årsverk", "Antall ansatte",
            "Sysselsatte", "Antall årsverk i regnskapsåret",
        ],
    },

    "skatt_aaret": {
        "resultat_for_skatt": [
            "Resultat før skatt", "Resultat før skattekostnad",
            "Årsresultat før skatt", "Regnskapsmessig resultat før skattekostnad",
            "Ordinært resultat før skatt",
        ],
        "skattepliktig_inntekt": [
            "Skattepliktig inntekt", "Skattepliktig resultat",
            "Skattepliktig inntekt grunnlag for betalbar skatt",
        ],
        "betalbar_skatt": [
            "Betalbar skatt", "Betalbar skatt på årets resultat",
            "Skatt betalbar", "Resultatført betalbar skatt",
        ],
        "endring_utsatt_skatt": [
            "Endring i utsatt skatt", "Endring utsatt skatt",
            "Endring i utsatt skattefordel", "Utsatt skatt endring",
        ],
        "skattekostnad_total": [
            "Skattekostnad", "Skattekostnad ordinært resultat",
            "Skattekostnad i resultatregnskapet", "Sum skattekostnad",
            "Total skattekostnad",
        ],
        "konsernbidrag_avgitt_with_skatte_effect": [
            "Avgitt konsernbidrag", "Avgift konsernbidrag",
            "Mottatt avgitt konsernbidrag",
        ],
        "konsernbidrag_mottatt_with_skatte_effect": [
            "Mottatt konsernbidrag", "Skatteeffekt mottatt konsernbidrag",
        ],
    },

    "anleggsmidler_rollforward": {
        "anskaffelseskost_01_01": [
            "Anskaffelseskost 01.01", "Anskaffelseskost 1.1",
            "Anskaffelseskost pr 01.01", "Anskaffelseskost ved årets begynnelse",
            "Inngående anskaffelseskost",
        ],
        "anskaffelseskost_31_12": [
            "Anskaffelseskost 31.12", "Anskaffelseskost pr 31.12",
            "Anskaffelseskost ved årets slutt", "Utgående anskaffelseskost",
        ],
        "tilgang": [
            "Tilgang", "Tilgang i året", "Årets tilgang",
            "Tilgang av varige driftsmidler",
        ],
        "avgang": [
            "Avgang", "Avgang i året", "Årets avgang",
        ],
        "balansefort_31_12": [
            "Balanseført verdi 31.12", "Bokført verdi 31.12",
            "Balanseført verdi per 31.12", "Bokført verdi pr 31.12",
            "Netto bokført verdi",
        ],
        "akkumulerte_avskrivninger_31_12": [
            "Akkumulerte avskrivninger 31.12", "Akkumulerte avskrivninger",
            "Akk. avskrivninger 31.12", "Sum akkumulerte avskrivninger",
        ],
        "akkumulerte_nedskrivninger_31_12": [
            "Akkumulerte nedskrivninger 31.12", "Akk. nedskrivninger",
            "Sum akkumulerte nedskrivninger",
        ],
        "arets_avskrivninger": [
            "Årets avskrivninger", "Avskrivninger i regnskapsåret",
            "Avskrivninger nedskrivninger og reverseringer av nedskrivninger",
        ],
        "arets_nedskrivninger": [
            "Årets nedskrivninger", "Nedskrivninger i regnskapsåret",
            "Nedskrivning",
        ],
    },

    "aksjekapital_struktur": {
        "antall_aksjer": [
            "Antall aksjer", "Antall ordinære aksjer", "Sum antall aksjer",
            "Totalt antall aksjer",
        ],
        "palydende": ["Pålydende", "Pålydende verdi", "Nominell verdi"],
        "bokfort_verdi": ["Bokført", "Bokført verdi", "Sum bokført"],
    },

    "bankinnskudd_bundne": {
        "bundne_skattetrekksmidler": [
            "Bundne skattetrekksmidler", "Skattetrekksmidler",
            "Bundne midler", "Innestående midler på skattetrekkskonto",
        ],
    },

    "revisor_honorar": {
        "revisjon": [
            "Lovpålagt revisjon", "Revisjon", "Revisjonshonorar",
            "Honorar lovpålagt revisjon", "Honorar revisjon",
        ],
        "skatteradgivning": [
            "Skatterådgivning", "Teknisk bistand skatt",
            "Honorar skatterådgivning",
        ],
        "annen_bistand": [
            "Andre attestasjonstjenester", "Annen bistand",
            "Andre tjenester", "Annet",
        ],
        "sum": ["Sum honorar", "Sum revisorhonorar", "Total"],
    },

    "skattefunn": {
        "forventet_tilskudd_nok": [
            "Forventet SkatteFUNN tilskudd", "Fordring SkatteFUNN",
            "SkatteFUNN tilskudd", "SkatteFUNN", "Tilskudd SkatteFUNN",
        ],
    },
}


def all_fields(table: str) -> list[str]:
    """Return all canonical fields for a table."""
    return list(CANONICAL_FIELDS.get(table, {}).keys())


def synonyms_for(table: str, field: str) -> list[str]:
    """Return all known synonyms for a (table, field)."""
    return CANONICAL_FIELDS.get(table, {}).get(field, [])


def all_synonyms_flat() -> list[tuple[str, str, str]]:
    """Return [(table, field, synonym), ...] over the entire schema."""
    out = []
    for table, fields in CANONICAL_FIELDS.items():
        for field, synonyms in fields.items():
            for s in synonyms:
                out.append((table, field, s))
    return out

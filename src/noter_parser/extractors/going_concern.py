def build(data: dict, orgnr: str, year: int) -> list[dict]:
    """Find a note that confirms or discusses fortsatt drift. Sources:
      - Standalone 'Fortsatt drift' titled note
      - Mention inside Regnskapsprinsipper / styrets beretning
      - Embedded in any other note's raw_text"""
    fd_note = None
    for n in data.get("noter", []):
        title = (n.get("tittel") or "").lower()
        if "fortsatt drift" in title:
            fd_note = n
            break
    if fd_note is None:
        for n in data.get("noter", []):
            text = (n.get("raw_text") or "").lower()
            if "fortsatt drift" in text:
                fd_note = n
                break
    if fd_note is None:
        return []
    text = fd_note.get("raw_text", "") or ""
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "fortsatt_drift_bekreftet": True,
        "usikkerhet_fortsatt_drift": "usikker" in text.lower() or "tvil" in text.lower(),
        "narrative_excerpt": text[:300],
    }]

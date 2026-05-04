def build(data: dict, orgnr: str, year: int) -> list[dict]:
    rows = []
    for n in data.get("noter", []):
        text = n.get("raw_text", "") or ""
        if "fortsatt drift" not in text.lower():
            continue
        rows.append({
            "orgnr": orgnr,
            "report_year": year,
            "source_filing_year": year,
            "fortsatt_drift_bekreftet": True,
            "usikkerhet_fortsatt_drift": "usikker" in text.lower() or "tvil" in text.lower(),
            "narrative_excerpt": text[:300],
        })
        break  # one row per (orgnr, year)
    return rows

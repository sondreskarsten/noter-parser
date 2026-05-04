from ..config import NA


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "company_name": data.get("company_name", "") or "",
        "n_notes_extracted": data.get("n_notes", len(data.get("noter", []))),
        "extraction_source": data.get("prompt_name", "") or data.get("extracted_by", ""),
        "pdf_hash": data.get("pdf_hash", "") or "",
        "n_pages_sent": data.get("n_pages_sent", NA),
    }]

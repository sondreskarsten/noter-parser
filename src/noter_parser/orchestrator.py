"""Run all extractors over one (orgnr, year) and return per-table rows."""
from .extractors import REGISTRY


def parse_one(data: dict, orgnr: str, year: int) -> dict[str, list[dict]]:
    """Returns {table_name: [row_dict, ...], ...}"""
    return {table: builder(data, orgnr, year) for table, builder in REGISTRY.items()}


def parse_orgnr_years(loader, orgnr: str, years: list[int]) -> dict[str, list[dict]]:
    """Aggregate rows across years for one orgnr.
    `loader` is a callable (orgnr, year) -> (json_data, source_label) | (None, None)."""
    aggregated: dict[str, list[dict]] = {}
    failures: list[dict] = []
    for year in years:
        data, source = loader(orgnr, year)
        if data is None:
            failures.append({
                "orgnr": orgnr, "year": year,
                "reason": "no_extraction_json",
            })
            continue
        per_year = parse_one(data, orgnr, year)
        for table, rows in per_year.items():
            if rows:
                aggregated.setdefault(table, []).extend(rows)
    return {"tables": aggregated, "failures": failures}

# noter-parser

Deterministic Python parser for Norwegian årsregnskap notes. Transforms structured Gemini extractions into flat CSV tables for the corporate banking surveillance platform.

## What this is

Gemini-2.5-flash extracts årsregnskap (annual financial report) PDFs into structured JSON via the [`extraction-prompts`](https://github.com/sondreskarsten/extraction-prompts) repo (specifically the `noter_v5b` prompt). The extracted JSONs land at `gs://sondre_brreg_data/raw/noter_extraction_2025/extractions/noter_v5b/{orgnr}_{year}.json` with a structured schema:

```jsonc
{
  "orgnr": "989100106",
  "year": 2024,
  "n_pages_sent": 41,
  "page_numbers": [...],
  "noter": [
    {
      "nr": "11",
      "tittel": "Varer",
      "type": "table",
      "raw_amounts": { "Råvarer 2024": 537239090, "Sum varelager 2024": 991423785, ... },
      "raw_text": "..."
    }
  ]
}
```

The "noter[].raw_amounts" dict is what this repo parses. Each line label in the source PDF becomes a key (`"Sum varelager 2024"`) and Gemini extracts the value verbatim. This repo enumerates the finite set of label patterns that show up across Norwegian noter and maps them to canonical columns in 14 tidy tables.

No Gemini calls. The expensive structured extraction has already happened — this is a deterministic compiler from JSON to CSV.

## Where data lives

| Asset | GCS path |
|---|---|
| Source PDFs (one per orgnr/year) | `gs://brreg-regnskap/regnskap/{orgnr}/aarsregnskap_{year}.pdf` |
| Gemini noter_v5b JSONs | `gs://sondre_brreg_data/raw/noter_extraction_2025/extractions/noter_v5b/{orgnr}_{year}.json` |
| Manual visual extractions (Claude fallback) | `gs://sondre_brreg_data/raw/noter_extraction_2025/extractions/manual_claude_v1/{orgnr}_{year}.json` |
| Output CSVs | `gs://sondre_brreg_data/raw/noter_extraction_2025/structured/{table}/{orgnr}.csv` |
| Build scripts (alongside outputs) | `gs://sondre_brreg_data/raw/noter_extraction_2025/structured/_build/` |

## Tables produced

| Table | Per-row grain |
|---|---|
| `documents` | (orgnr, year) — filing metadata |
| `aksjekapital_struktur` | (orgnr, year, aksjeklasse) |
| `aksjonaerer` | (orgnr, year, aksjonær) — direct parent only, time-series |
| `egenkapital_summary` | (orgnr, year) — sum + components + konsernbidrag flow |
| `lonn_ytelser` | (orgnr, year) — lønn + AGA + pensjon + sum + årsverk |
| `godtgjorelse_ledende` | (orgnr, year, role) — daglig leder + styre |
| `revisor_honorar` | (orgnr, year) — revisor fees split |
| `bankinnskudd_bundne` | (orgnr, year) — bundne skattetrekksmidler |
| `skatt_aaret` | (orgnr, year) — full skatte-reconciliation |
| `anleggsmidler_rollforward` | (orgnr, year, asset_class) |
| `relatert_part_kreditt` | (orgnr, year, party, direction) — RPK transactions and balances |
| `skattefunn` | (orgnr, year) — forventet tilskudd |
| `kontingente_forpliktelser` | (orgnr, year) — lawsuits, contingent liabilities |
| `going_concern` | (orgnr, year) — fortsatt drift narrative |

## Visual audit

This pipeline includes a visual audit script that **renders every page** of a regnskap PDF and produces a contact sheet, so an operator (or Claude via the `view` tool) can confirm no notes were missed. This catches rig page-selection failures like the EPAX 2015 case where Gemini was sent pages 6–7 of a 23-page PDF instead of the actual notes pages 15–17.

```bash
python scripts/audit_one.py 989100106 2015
# Renders /tmp/audit/989100106_2015/page_NN.jpg for all pages
# Compares JSON `page_numbers` against PDF total pages
# Prints anomaly report
```

## Fallback: no Gemini JSON exists

If a (orgnr, year) has no entry in `extractions/noter_v5b/`, the parser cannot run automatically. Use the visual fallback:

```bash
python scripts/render_pages.py 989100106 2015
# Writes JPGs of every page to /tmp/audit/989100106_2015/
```

Then read pages visually, transcribe to a JSON in the noter_v5b schema, save to `extractions/manual_claude_v1/`, and re-run the parser.

## Running

```bash
# Single orgnr, all years
python scripts/parse_orgnr.py 989100106

# Many orgnrs from a file (one per line)
python scripts/parse_batch.py orgnrs.txt --workers 24

# Audit a single (orgnr, year) — renders every page
python scripts/audit_one.py 989100106 2015
```

## Status

Bootstrapped 2026-05-04 from the EPAX rebuild (`build_epax_v2_gemini.py`). Validated against EPAX (989100106) for 2010-2024.

Not yet tested at population scale (~12,860 orgnrs). Failure modes will be discovered by running broadly and patching parsers, never by hand-coding per-orgnr overrides except in genuinely unique cases (e.g. fusjon years where the corporate structure is not representable by the standard schema).

## Coding conventions

- Junior-implementing-senior. No defensive trycatches, no narrative comments, no message logging without request.
- Each extractor is a complete standalone function with default arguments.
- Every parser fix should generalize across the population. Per-orgnr overrides are an anti-pattern — if you need one, the parser is wrong.
- Visual inspection of every page is part of debugging, not a fallback.

## Related repos

- [extraction-prompts](https://github.com/sondreskarsten/extraction-prompts) — the Gemini prompt and Cloud Run extraction job
- [tidybrreg](https://github.com/sondreskarsten/tidybrreg) — R package for Brreg API access

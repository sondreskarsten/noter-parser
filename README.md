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

## Schema-mapping cascade (NEW)

The parser now has a 3-tier fallback cascade for handling label variance across the SME population:

```
   raw_amounts key
        ↓
   Tier 0: deterministic regex (matchers.get_amount)
        ↓ miss
   Tier 1: rapidfuzz WRatio ≥ 95   (lexical near-match)
        ↓ miss
   Tier 2: BGE-M3 embedding ≥ 0.78 (semantic similarity)
        ↓ miss
   Tier 3: LLM router               (Claude Haiku 4.5, optional)
        ↓ miss
   None  →  noter-text-extraction reprocess via Claude vision
```

Tier 1+2 are implemented in `schema_mapper.py` and target a fixed canonical schema in `canonical_schema.py`. Each canonical field has a list of observed Norwegian synonyms ("Aksjekapital", "Aksje-kapital", "Innskutt aksjekapital" → all → `aksjekapital`).

Tier 3 (`llm_router.py`) is a stub that uses the Anthropic API with constrained Literal output — the model can only pick from the list of canonical fields, never invent new ones. It's only invoked when Tier 2 cosine similarity is < 0.82 OR the top-1/top-2 margin is < 0.05.

To enable Tier 1 only:
```bash
pip install rapidfuzz
```

To enable Tier 2 (semantic):
```bash
pip install sentence-transformers torch
```

To enable Tier 3 (LLM router):
```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
```

Tier 1 is on by default. Tier 2 is lazy-loaded on first call. Tier 3 is opt-in (only invoked when caller explicitly calls `llm_router.confident_route`).

## Validators (Pandera-style identity checks)

After parsing, `validators.py` runs financial identity checks:

- `egenkapital_summary`: aksjekap + innskutt + opptjent ≈ sum_egenkapital
- `lonn_ytelser`: lønn + AGA + pensjon + andre ≈ sum_lønnskostnader
- `skatt_aaret`: betalbar + endring_utsatt ≈ skattekostnad_total
- `anleggsmidler_rollforward`: anskaffelse - akk_avskrivninger ≈ balanseført

Tolerance: 0.1% relative or 1 NOK absolute (rounding-grade).

```python
from noter_parser import parse_orgnr_with_validation
res = parse_orgnr_with_validation(loader, "989100106", [2024])
print(res["validation"]["egenkapital_summary"]["pass_rate"])  # 1.0 if all rows balance
```

Failed identities don't crash the pipeline — they're emitted to a review queue. A failed roll-forward is high-confidence evidence of an extraction error.

## Source priority

`load_noter_json` reads from these prefixes in priority order:

1. `noter_v5b` — Gemini-extracted (canonical for orgnrs already processed)
2. `tesseract_v1` — output of [noter-text-extraction](https://github.com/sondreskarsten/noter-text-extraction) (deterministic OCR pipeline)
3. `claude_visual_v1` — interactive Claude vision (used for failures)
4. `manual_claude_v1` — hand-transcribed (last resort)

The parser doesn't care which source it reads from; the JSON schema is identical. This means you can swap text-extraction backends per-firm without changing parser code.

## Related repos

- [noter-text-extraction](https://github.com/sondreskarsten/noter-text-extraction) — deterministic PDF → JSON OCR pipeline (replaces Gemini)
- [extraction-prompts](https://github.com/sondreskarsten/extraction-prompts) — original Gemini prompt
- [tidybrreg](https://github.com/sondreskarsten/tidybrreg) — R package for Brreg API access

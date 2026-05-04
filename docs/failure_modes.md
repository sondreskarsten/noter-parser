# Known failure modes

## 1. Rig page-selection bug (EPAX 2014, 2015)

**Symptom**: `n_pages_sent < 5` despite a multi-page PDF; `n_notes` near zero; `audit` flags `low_page_coverage`.

**Root cause**: The `extraction-prompts/cloud_run_brreg_json` page-selection heuristic fails on certain filings — for EPAX 2015, it sent pages 6–7 of a 23-page PDF instead of 15–17 where the actual notes lived. For 2014 it sent only the revisor uttalelse pages.

**Detection**: `python scripts/audit_one.py <orgnr> <year>` will flag this with `low_page_coverage`.

**Mitigation**: 
1. Inspect the rendered pages visually (the audit script writes them to `/tmp/audit/{orgnr}_{year}/`)
2. If real noter pages exist that weren't sent, transcribe them manually to a JSON in the noter_v5b schema and save to `extractions/manual_claude_v1/`
3. The parser will fall back to the manual extraction automatically.

A long-term fix should land in the `extraction-prompts` repo — the page-selection heuristic needs better signals for distinguishing notes pages from revisor uttalelse / styrets beretning / signature pages.

## 2. Aksjonær compound-key parsing

**Symptom**: Aksjonær = "UNKNOWN" or a column header like "Antall aksjer".

**Root cause**: Two distinct PDF layouts. Older filings have the parent name immediately after the "Eneste aksjonær er:" anchor. Newer filings interleave column headers between the anchor and the name. The parser uses Gemini's compound `raw_amounts` keys (e.g. `"Pelagia AS Antall aksjer": 3814654`) as the primary signal because it's robust to layout changes.

**When this fails**: The Gemini prompt didn't capture compound keys, OR the parent name doesn't appear in any compound key. Falls back to text parsing of `raw_text`.

## 3. Sub-table key collisions

**Symptom**: A "Sum" key in lønnskostnad note actually refers to revisor honorar sub-table sum, not lønn sum.

**Root cause**: Gemini flattens hierarchical tables into a flat `raw_amounts` dict without a sub-table prefix. Same row-label can appear in multiple sub-tables.

**Mitigation**: Parsers prefer specific keys over generic ones (e.g. `"Sum lønnskostnad"` not `"Sum"`). When no specific key exists, sum from components.

## 4. % normalization

**Symptom**: Diskonteringsrente shows `0.039` instead of `3.9`.

**Root cause**: noter_v5b spec says "values as printed". A printed `3,9 %` should stay 3.9. Some manual extractions normalized to 0.039.

**Mitigation**: Don't normalize. Parser should preserve Gemini's raw value.

## 5. NACE-filtered upstream coverage

**Symptom**: `python scripts/parse_orgnr.py <orgnr>` returns "no extraction JSONs" for some orgnrs.

**Root cause**: The Gemini extraction was run only against a subset of orgnrs (definition lives in `extraction-prompts/cloud_run_brreg_json`). Coverage is not population-complete.

**Mitigation**: For any orgnr-of-interest, check `extraction-prompts/cloud_run_brreg_json` to confirm it would be in scope. If not, the rig needs to be re-run for that orgnr (or use the manual visual fallback).

"""Phase 1 stress test — measure noter-parser coverage and accuracy.

Run on a seed=42 sample of 100 orgnrs from the noter_v5b inventory.
For each (orgnr, year):
  1. Load noter_v5b JSON (Gemini reference)
  2. Parse via all 14 extractors
  3. Run identity validators
  4. If regnskapsapi validation JSON exists, cross-check totals
  5. Write summary CSV to GCS

Usage:
  python scripts/stress_test.py                        # full 100-sample
  python scripts/stress_test.py --n 10                 # quick smoke test
  python scripts/stress_test.py --orgnrs 989100106     # single orgnr
"""
import argparse
import csv
import io
import json
import logging
import os
import random
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from google.cloud import storage

from noter_parser.extractors import REGISTRY
from noter_parser.orchestrator import parse_one
from noter_parser.sources import load_noter_json, list_years_for_orgnr
from noter_parser.validators import run_validators

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

BUCKET = "sondre_brreg_data"
NOTER_V5B_PREFIX = "raw/noter_extraction_2025/extractions/noter_v5b"
VALIDATION_PREFIX = "regnskapsapi/validation"
OUTPUT_PREFIX = "raw/noter_extraction_2025/_meta"


def sample_orgnrs(n: int = 100, seed: int = 42) -> list[str]:
    client = storage.Client()
    bkt = client.bucket(BUCKET)
    all_orgnrs = sorted({
        b.name.split("/")[-1].split("_")[0]
        for b in bkt.list_blobs(prefix=f"{NOTER_V5B_PREFIX}/")
        if b.name.endswith(".json")
    })
    random.seed(seed)
    return random.sample(all_orgnrs, min(n, len(all_orgnrs)))


def load_regnskapsapi_validation(orgnr: str, year: int) -> dict | None:
    client = storage.Client()
    blob = client.bucket(BUCKET).blob(f"{VALIDATION_PREFIX}/{orgnr}_{year}.json")
    if blob.exists():
        return json.loads(blob.download_as_text())
    return None


def cross_check_api(parsed_tables: dict, api_data: dict) -> dict:
    checks = {}
    ek_rows = parsed_tables.get("egenkapital_summary", [])
    if ek_rows and api_data.get("sum_egenkapital") is not None:
        for row in ek_rows:
            if "sum_egenkapital" in row and row["sum_egenkapital"] is not None:
                noter_val = float(row["sum_egenkapital"])
                api_val = float(api_data["sum_egenkapital"])
                diff = abs(noter_val - api_val)
                tol = max(abs(api_val) * 0.01, 1.0) if api_val else 1.0
                checks["sum_egenkapital"] = {
                    "noter": noter_val, "api": api_val,
                    "diff": diff, "pass": diff <= tol,
                }
                break

    if api_data.get("aarsresultat") is not None:
        for table_name in ("resultatregnskap", "skatt_aaret"):
            rows = parsed_tables.get(table_name, [])
            for row in rows:
                for field in ("aarsresultat", "resultat_for_skatt"):
                    if field in row and row[field] is not None:
                        noter_val = float(row[field])
                        api_val = float(api_data["aarsresultat"])
                        diff = abs(noter_val - api_val)
                        tol = max(abs(api_val) * 0.01, 1.0) if api_val else 1.0
                        checks[field] = {
                            "noter": noter_val, "api": api_val,
                            "diff": diff, "pass": diff <= tol,
                        }
    return checks


def run_stress_test(orgnrs: list[str]) -> list[dict]:
    results = []
    t0 = time.time()

    for i, orgnr in enumerate(orgnrs):
        years = list_years_for_orgnr(orgnr)
        for year in years:
            data, source = load_noter_json(orgnr, year)
            if data is None:
                results.append({
                    "orgnr": orgnr, "year": year, "source": None,
                    "status": "no_data",
                })
                continue

            n_notes = len(data) if isinstance(data, list) else len(data.get("noter", data))
            tables = parse_one(data, orgnr, year)

            table_stats = {}
            for table_name, rows in tables.items():
                n_rows = len(rows) if rows else 0
                n_fields = 0
                n_filled = 0
                if rows:
                    for row in rows:
                        for k, v in row.items():
                            if k not in ("orgnr", "year", "source"):
                                n_fields += 1
                                if v is not None:
                                    n_filled += 1
                table_stats[table_name] = {
                    "n_rows": n_rows,
                    "n_fields": n_fields,
                    "n_filled": n_filled,
                    "fill_rate": n_filled / n_fields if n_fields > 0 else 0,
                }

            validation = run_validators(tables)
            api_data = load_regnskapsapi_validation(orgnr, year)
            api_checks = cross_check_api(tables, api_data) if api_data else {}

            for table_name, stats in table_stats.items():
                val_result = validation.get(table_name, {})
                row = {
                    "orgnr": orgnr,
                    "year": year,
                    "source": source,
                    "table": table_name,
                    "n_rows": stats["n_rows"],
                    "n_fields": stats["n_fields"],
                    "n_filled": stats["n_filled"],
                    "fill_rate": round(stats["fill_rate"], 3),
                    "validator_pass": val_result.get("pass_rate", None),
                    "validator_n_checks": val_result.get("n_checks", 0),
                    "validator_n_passed": val_result.get("n_passed", 0),
                }
                for check_name, check_data in api_checks.items():
                    row[f"api_{check_name}_pass"] = check_data["pass"]
                    row[f"api_{check_name}_diff"] = check_data["diff"]
                results.append(row)

        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            log.info("Progress: %d/%d orgnrs (%.0fs)", i + 1, len(orgnrs), elapsed)

    return results


def write_results(results: list[dict], tag: str = None):
    from datetime import date
    if tag is None:
        tag = date.today().isoformat()

    all_keys = set()
    for r in results:
        all_keys.update(r.keys())
    all_keys = sorted(all_keys)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=all_keys)
    writer.writeheader()
    writer.writerows(results)
    csv_text = buf.getvalue()

    client = storage.Client()
    blob = client.bucket(BUCKET).blob(f"{OUTPUT_PREFIX}/stress_test_{tag}.csv")
    blob.upload_from_string(csv_text, content_type="text/csv")
    log.info("Wrote %d rows to gs://%s/%s/stress_test_%s.csv", len(results), BUCKET, OUTPUT_PREFIX, tag)

    no_data = [r for r in results if r.get("status") == "no_data"]
    with_data = [r for r in results if r.get("status") != "no_data"]

    print(f"\n{'='*60}")
    print(f"STRESS TEST SUMMARY (n={len(results)} rows, {len(set(r['orgnr'] for r in results))} orgnrs)")
    print(f"{'='*60}")
    print(f"No data:    {len(no_data)}")
    print(f"With data:  {len(with_data)}")

    if with_data:
        table_counts = defaultdict(list)
        for r in with_data:
            table_counts[r["table"]].append(r)

        print(f"\nPer-table coverage:")
        for table in sorted(table_counts):
            rows = table_counts[table]
            n = len(rows)
            has_rows = sum(1 for r in rows if r.get("n_rows", 0) > 0)
            fill_rates = [r["fill_rate"] for r in rows if r.get("fill_rate") is not None]
            val_passes = [r["validator_pass"] for r in rows if r.get("validator_pass") is not None]

            print(f"  {table:30s}  coverage={has_rows}/{n}  "
                  f"fill_rate={'%.1f%%' % (100*sum(fill_rates)/len(fill_rates)) if fill_rates else 'n/a':>6s}  "
                  f"validator={'%.0f%%' % (100*sum(1 for v in val_passes if v >= 1.0)/len(val_passes)) if val_passes else 'n/a':>4s}")

    return csv_text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orgnrs", nargs="+")
    parser.add_argument("--tag", default=None)
    args = parser.parse_args()

    if args.orgnrs:
        orgnrs = args.orgnrs
    else:
        orgnrs = sample_orgnrs(args.n, args.seed)
        log.info("Sampled %d orgnrs (seed=%d)", len(orgnrs), args.seed)

    results = run_stress_test(orgnrs)
    write_results(results, tag=args.tag)


if __name__ == "__main__":
    main()

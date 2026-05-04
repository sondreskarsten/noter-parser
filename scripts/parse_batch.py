#!/usr/bin/env python3
"""Parse many orgnrs in parallel.

Usage:
  python scripts/parse_batch.py orgnrs.txt [--workers 24] [--replace]
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from noter_parser import (
    list_years_for_orgnr,
    load_noter_json,
    parse_orgnr_years,
    write_all,
)


def parse_one_orgnr(orgnr: str, replace: bool = False):
    years = list_years_for_orgnr(orgnr)
    if not years:
        return orgnr, {"status": "no_years", "tables": {}, "written": {}}
    result = parse_orgnr_years(load_noter_json, orgnr, years)
    written = write_all(result["tables"], orgnr, replace=replace)
    return orgnr, {
        "status": "ok",
        "n_years": len(years),
        "n_tables": len(written),
        "n_failures": len(result["failures"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="Path to file with one orgnr per line")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--replace", action="store_true")
    args = ap.parse_args()

    with open(args.file) as f:
        orgnrs = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    print(f"Parsing {len(orgnrs)} orgnrs with {args.workers} workers")
    results: list[tuple] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(parse_one_orgnr, o, args.replace): o for o in orgnrs}
        for fut in as_completed(futures):
            orgnr, info = fut.result()
            print(f"  {orgnr}  {info['status']:<14}  "
                  f"y={info.get('n_years', 0):<3}  "
                  f"t={info.get('n_tables', 0):<3}  "
                  f"f={info.get('n_failures', 0)}")
            results.append((orgnr, info))

    ok = sum(1 for _, i in results if i["status"] == "ok")
    print(f"\n{ok}/{len(orgnrs)} orgnrs parsed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())

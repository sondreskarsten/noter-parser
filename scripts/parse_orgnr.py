#!/usr/bin/env python3
"""Parse all years for one orgnr and write CSVs to GCS.

Usage:
  python scripts/parse_orgnr.py <orgnr> [--years 2020,2021,...] [--replace]
"""
import argparse
import sys

from noter_parser import (
    list_years_for_orgnr,
    load_noter_json,
    parse_orgnr_years,
    write_all,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orgnr")
    ap.add_argument("--years", default="", help="Comma-separated; default = all")
    ap.add_argument("--replace", action="store_true", help="Overwrite existing CSVs")
    args = ap.parse_args()

    if args.years:
        years = [int(y) for y in args.years.split(",")]
    else:
        years = list_years_for_orgnr(args.orgnr)

    if not years:
        print(f"No extraction JSONs found for orgnr {args.orgnr}", file=sys.stderr)
        return 1

    print(f"Parsing {args.orgnr} for years {years}")
    result = parse_orgnr_years(load_noter_json, args.orgnr, years)
    written = write_all(result["tables"], args.orgnr, replace=args.replace)
    for table, path in written.items():
        print(f"  {table:32} {len(result['tables'][table]):>3} rows  {path}")
    if result["failures"]:
        print(f"\nFailures ({len(result['failures'])}):")
        for f in result["failures"]:
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

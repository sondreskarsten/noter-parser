#!/usr/bin/env python3
"""Visual audit of one (orgnr, year): render every page of the source PDF
and compare against Gemini's claimed page coverage.

Usage:
  python scripts/audit_one.py <orgnr> <year> [--no-render]
"""
import argparse
import json
import sys

from noter_parser import audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orgnr")
    ap.add_argument("year", type=int)
    ap.add_argument("--no-render", action="store_true",
                    help="Skip page rasterization (metadata-only audit)")
    ap.add_argument("--dpi", type=int, default=100)
    args = ap.parse_args()

    result = audit(args.orgnr, args.year, render=not args.no_render, dpi=args.dpi)
    # Don't dump full pages list to console
    short = {k: v for k, v in result.items() if k != "render"}
    if result.get("render"):
        short["render_summary"] = {
            "out_dir": result["render"]["out_dir"],
            "page_count": result["render"]["page_count"],
            "first_page": result["render"]["pages"][0] if result["render"]["pages"] else None,
            "last_page": result["render"]["pages"][-1] if result["render"]["pages"] else None,
        }
    print(json.dumps(short, indent=2, default=str))
    if result["status"] == "anomaly":
        print(f"\nFLAGGED: {result['flags']}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

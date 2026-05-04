#!/usr/bin/env python3
"""Rasterize every page of a regnskap PDF. Use when no Gemini JSON exists
for (orgnr, year) — operator visually reads pages and transcribes manually
to a JSON in extractions/manual_claude_v1/.

Usage:
  python scripts/render_pages.py <orgnr> <year> [--dpi 100]
"""
import argparse
import sys

from noter_parser import render_all_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orgnr")
    ap.add_argument("year", type=int)
    ap.add_argument("--dpi", type=int, default=100)
    args = ap.parse_args()

    res = render_all_pages(args.orgnr, args.year, dpi=args.dpi)
    print(f"Rendered {res['page_count']} pages to {res['out_dir']}")
    for p in res["pages"]:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Visual audit: render every page of a regnskap PDF and compare against the
JSON extraction's claimed page coverage. This is the primary defence against
rig page-selection failures (e.g. EPAX 2015 where rig sent pages 6-7 of a
23-page PDF, missing the actual notes pages 15-17).

The 'parser' has no idea which pages contain notes — that's the rig's job.
But we CAN sanity-check: if Gemini saw < 40% of the PDF or claims < 5 notes,
the extraction is suspect and a human should look at every page."""
import os
import subprocess
import shutil
from pathlib import Path

from .sources import download_pdf, load_noter_json


def render_all_pages(orgnr: str, year: int, dpi: int = 100, out_dir: str | None = None) -> dict:
    """Rasterize every page of the regnskap PDF to JPGs.
    Returns {'out_dir': path, 'page_count': N, 'pages': [path, path, ...]}."""
    if out_dir is None:
        out_dir = f"/tmp/audit/{orgnr}_{year}"
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = f"{out_dir}/source.pdf"
    download_pdf(orgnr, year, pdf_path)
    page_count = _pdf_page_count(pdf_path)
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", str(dpi), pdf_path, f"{out_dir}/page"],
        check=True,
        capture_output=True,
    )
    pages = sorted(Path(out_dir).glob("page-*.jpg"))
    return {
        "out_dir": out_dir,
        "page_count": page_count,
        "pages": [str(p) for p in pages],
    }


def _pdf_page_count(pdf_path: str) -> int:
    res = subprocess.run(
        ["pdfinfo", pdf_path], capture_output=True, text=True, check=True
    )
    for line in res.stdout.split("\n"):
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return 0


def audit(orgnr: str, year: int, render: bool = True, dpi: int = 100) -> dict:
    """Compare Gemini extraction against PDF page count.
    If render=True, also rasterizes every page so an operator can visually inspect."""
    data, source = load_noter_json(orgnr, year)
    if data is None:
        return {
            "orgnr": orgnr, "year": year,
            "status": "no_extraction_json",
            "render": render_all_pages(orgnr, year, dpi=dpi) if render else None,
        }
    n_pages_sent = data.get("n_pages_sent")
    page_numbers = data.get("page_numbers", [])
    n_notes = data.get("n_notes", len(data.get("noter", [])))
    rendered = render_all_pages(orgnr, year, dpi=dpi) if render else None
    pdf_pages = rendered["page_count"] if rendered else None
    flags = []
    if pdf_pages and n_pages_sent and n_pages_sent < 0.4 * pdf_pages:
        flags.append(
            f"low_page_coverage: rig sent {n_pages_sent}/{pdf_pages} pages "
            f"({n_pages_sent / pdf_pages:.0%})"
        )
    if n_notes < 5:
        flags.append(f"thin_extraction: only {n_notes} notes recovered")
    if pdf_pages and page_numbers and max(page_numbers) > pdf_pages:
        flags.append(
            f"page_index_oob: max page_number {max(page_numbers)} > pdf {pdf_pages}"
        )
    return {
        "orgnr": orgnr,
        "year": year,
        "status": "ok" if not flags else "anomaly",
        "source": source,
        "n_pages_sent": n_pages_sent,
        "page_numbers": page_numbers,
        "pdf_page_count": pdf_pages,
        "n_notes": n_notes,
        "flags": flags,
        "render": rendered,
    }


def cleanup(orgnr: str, year: int):
    out_dir = f"/tmp/audit/{orgnr}_{year}"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

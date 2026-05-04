"""Write per-table CSVs to GCS. Append-only by default: existing rows are
preserved and new rows appended at end. To rebuild from scratch, pass
`replace=True`."""
import csv
import io

from .config import DATA_BUCKET, STRUCTURED_PREFIX
from .sources import gcs_client


def write_table(table: str, orgnr: str, rows: list[dict], replace: bool = False) -> str:
    if not rows:
        return ""
    bkt = gcs_client().bucket(DATA_BUCKET)
    path = f"{STRUCTURED_PREFIX}/{table}/{orgnr}.csv"
    blob = bkt.blob(path)
    existing = ""
    fieldnames: list[str] = []
    if not replace and blob.exists():
        existing = blob.download_as_text()
        if existing:
            first = existing.split("\n", 1)[0]
            fieldnames = [c for c in first.split(",") if c]
    for r in rows:
        for k in r:
            if k not in fieldnames:
                fieldnames.append(k)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    if existing and not replace:
        for line in existing.split("\n")[1:]:
            if line:
                out.write(line + "\n")
    for r in rows:
        for k in fieldnames:
            r.setdefault(k, "")
        writer.writerow(r)
    blob.upload_from_string(out.getvalue())
    return f"gs://{DATA_BUCKET}/{path}"


def write_all(tables: dict[str, list[dict]], orgnr: str, replace: bool = False) -> dict[str, str]:
    return {t: write_table(t, orgnr, rows, replace=replace) for t, rows in tables.items() if rows}

import json
import os
import tempfile
from typing import Optional

from google.cloud import storage

from .config import (
    DATA_BUCKET, PDF_BUCKET, NOTER_V5B_PREFIX, MANUAL_VISUAL_PREFIX, PDF_PREFIX,
)


_client = None

def gcs_client():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def load_noter_json(orgnr: str, year: int) -> tuple[Optional[dict], Optional[str]]:
    """Load Gemini-extracted noter JSON for one (orgnr, year). Falls back to
    manual visual extraction if the v5b path is missing."""
    bkt = gcs_client().bucket(DATA_BUCKET)
    primary = f"{NOTER_V5B_PREFIX}/{orgnr}_{year}.json"
    fallback = f"{MANUAL_VISUAL_PREFIX}/{orgnr}_{year}.json"
    blob = bkt.blob(primary)
    if blob.exists():
        return json.loads(blob.download_as_text()), "noter_v5b"
    blob = bkt.blob(fallback)
    if blob.exists():
        return json.loads(blob.download_as_text()), "manual_claude_v1"
    return None, None


def list_years_for_orgnr(orgnr: str) -> list[int]:
    """All years for which a Gemini noter JSON exists."""
    bkt = gcs_client().bucket(DATA_BUCKET)
    years = set()
    for prefix in (NOTER_V5B_PREFIX, MANUAL_VISUAL_PREFIX):
        for b in bkt.list_blobs(prefix=f"{prefix}/{orgnr}_"):
            name = b.name.split("/")[-1]
            if name.endswith(".json"):
                yr = name.replace(f"{orgnr}_", "").replace(".json", "")
                if yr.isdigit():
                    years.add(int(yr))
    return sorted(years)


def list_pdf_years_for_orgnr(orgnr: str) -> list[int]:
    """All years for which a regnskap PDF exists in gs://brreg-regnskap/."""
    bkt = gcs_client().bucket(PDF_BUCKET)
    years = []
    for b in bkt.list_blobs(prefix=f"{PDF_PREFIX}/{orgnr}/"):
        name = b.name.split("/")[-1]
        if name.startswith("aarsregnskap_") and name.endswith(".pdf"):
            yr = name.replace("aarsregnskap_", "").replace(".pdf", "")
            if yr.isdigit():
                years.append(int(yr))
    return sorted(years)


def download_pdf(orgnr: str, year: int, dest: Optional[str] = None) -> str:
    """Download regnskap PDF to local path."""
    if dest is None:
        dest = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False).name
    bkt = gcs_client().bucket(PDF_BUCKET)
    bkt.blob(f"{PDF_PREFIX}/{orgnr}/aarsregnskap_{year}.pdf").download_to_filename(dest)
    return dest

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
    """Load extracted noter JSON for one (orgnr, year). Source priority:
      1. noter_v5b (Gemini)
      2. tesseract_v1 (this repo's deterministic OCR pipeline)
      3. claude_visual_v1 (interactive Claude vision)
      4. manual_claude_v1 (hand-transcribed)
    """
    bkt = gcs_client().bucket(DATA_BUCKET)
    sources = [
        (NOTER_V5B_PREFIX, "noter_v5b"),
        ("raw/noter_extraction_2025/extractions/tesseract_v1", "tesseract_v1"),
        ("raw/noter_extraction_2025/extractions/claude_visual_v1", "claude_visual_v1"),
        (MANUAL_VISUAL_PREFIX, "manual_claude_v1"),
    ]
    for prefix, label in sources:
        blob = bkt.blob(f"{prefix}/{orgnr}_{year}.json")
        if blob.exists():
            return json.loads(blob.download_as_text()), label
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


def load_regnskapsapi_validation(orgnr: str, year: int) -> Optional[dict]:
    """Load flattened regnskapsapi primary statement for cross-validation.
    Returns None if not yet fetched. NOT a noter source — primary statements only."""
    bkt = gcs_client().bucket(DATA_BUCKET)
    blob = bkt.blob(f"regnskapsapi/validation/{orgnr}_{year}.json")
    if blob.exists():
        return json.loads(blob.download_as_text())
    return None

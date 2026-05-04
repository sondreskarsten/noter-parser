"""Map raw_amounts keys to canonical (table, field) labels.

Cascade architecture (per the deep-research recommendation):
  Tier 1: RapidFuzz WRatio >= 95 -> auto-accept
  Tier 2: Sentence embedding cosine >= threshold -> accept
  Tier 3: (LLM router — implemented separately as needed)

Tier 1 alone covers 60-80% of label variations. Tier 2 picks up semantic
near-synonyms ('Skatt på ordinært resultat' vs 'Skattekostnad ordinært
resultat'). Tier 3 only fires for the residual ~5%.

The mapper is OPT-IN — extractors continue to use regex first, and only
fall through to schema_mapper.match_label() when regex misses. This
preserves determinism for the bulk of cases."""
import os
import pickle
from pathlib import Path
from typing import Optional

from .canonical_schema import all_synonyms_flat, CANONICAL_FIELDS


# Lazy global state
_FUZZ_INDEX: Optional[list[tuple[str, str, str]]] = None
_EMBEDDER = None
_RERANKER = None
_EMBEDDED_INDEX = None  # tuple (synonyms_list, embeddings_tensor)


def _load_fuzz_index():
    global _FUZZ_INDEX
    if _FUZZ_INDEX is None:
        _FUZZ_INDEX = all_synonyms_flat()
    return _FUZZ_INDEX


def fuzzy_match(label: str, table_filter: Optional[str] = None,
                threshold: int = 95) -> Optional[tuple[str, str, int]]:
    """RapidFuzz WRatio match. Returns (table, field, score) or None.

    Args:
        label: raw_amounts key (or stripped version with year removed)
        table_filter: only match within this table
        threshold: min WRatio score (0-100)
    """
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        return None
    index = _load_fuzz_index()
    if table_filter:
        index = [r for r in index if r[0] == table_filter]
    if not index:
        return None
    candidates = [r[2] for r in index]
    res = process.extractOne(label, candidates, scorer=fuzz.WRatio)
    if res is None or res[1] < threshold:
        return None
    matched_synonym, score, idx = res
    table, field, _ = index[idx]
    return (table, field, int(score))


def _load_embedder():
    """Load BGE-M3 lazily. Returns None if sentence-transformers not installed
    or model can't be loaded — caller should fall back to fuzzy-only."""
    global _EMBEDDER
    if _EMBEDDER is False:
        return None
    if _EMBEDDER is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer("BAAI/bge-m3")
        except Exception:
            _EMBEDDER = False
            return None
    return _EMBEDDER


def _build_embedded_index():
    """Pre-compute embeddings for every canonical synonym."""
    global _EMBEDDED_INDEX
    if _EMBEDDED_INDEX is not None:
        return _EMBEDDED_INDEX
    embedder = _load_embedder()
    if embedder is None:
        return None
    index = _load_fuzz_index()
    synonyms = [r[2] for r in index]
    embeddings = embedder.encode(synonyms, normalize_embeddings=True,
                                  show_progress_bar=False)
    _EMBEDDED_INDEX = (synonyms, embeddings)
    return _EMBEDDED_INDEX


def embed_match(label: str, table_filter: Optional[str] = None,
                threshold: float = 0.78, top_k: int = 5) -> Optional[tuple[str, str, float]]:
    """BGE-M3 cosine match. Returns (table, field, score) or None.

    Returns None if sentence-transformers unavailable. Score is cosine
    similarity in [0, 1]."""
    idx = _build_embedded_index()
    if idx is None:
        return None
    synonyms, embeddings = idx
    embedder = _load_embedder()
    query = embedder.encode([label], normalize_embeddings=True,
                            show_progress_bar=False)[0]
    # cosine = dot product since normalized
    scores = embeddings @ query
    full_index = _load_fuzz_index()
    if table_filter:
        # mask out non-matching tables
        mask = [r[0] == table_filter for r in full_index]
        scores = [s if m else -1.0 for s, m in zip(scores, mask)]
    # top-1
    best_idx = int(_argmax(scores))
    best_score = float(scores[best_idx])
    if best_score < threshold:
        return None
    table, field, _ = full_index[best_idx]
    return (table, field, best_score)


def match_label(label: str, table_filter: Optional[str] = None,
                fuzz_threshold: int = 95,
                embed_threshold: float = 0.78) -> Optional[tuple[str, str, float, str]]:
    """Cascade match: try fuzzy first, then embedding fallback.

    Returns (table, field, score_normalized_0_to_1, tier) or None.
    """
    fr = fuzzy_match(label, table_filter, fuzz_threshold)
    if fr is not None:
        table, field, score = fr
        return (table, field, score / 100.0, "fuzzy")
    er = embed_match(label, table_filter, embed_threshold)
    if er is not None:
        table, field, score = er
        return (table, field, score, "embed")
    return None


def _argmax(seq) -> int:
    best_i = 0
    best_v = seq[0]
    for i, v in enumerate(seq):
        if v > best_v:
            best_i = i
            best_v = v
    return best_i


def find_in_amounts(amounts: dict, table: str, field: str,
                    year: Optional[int] = None,
                    fuzz_threshold: int = 88,
                    embed_threshold: float = 0.72) -> Optional[float]:
    """Search through a raw_amounts dict for a value matching (table, field).

    For each amounts key:
      1. Strip the year suffix (if present)
      2. Run match_label against the table's fields
      3. If matched field == requested field, return the value

    Year filtering: if `year` is provided, only consider keys containing
    that year as a substring."""
    candidates: list[tuple[str, float]] = []
    for k, v in amounts.items():
        if not isinstance(v, (int, float)):
            continue
        if year is not None and str(year) not in k:
            continue
        # Strip trailing 4-digit year for cleaner matching
        stripped = _strip_year_suffix(k)
        m = match_label(stripped, table_filter=table,
                        fuzz_threshold=fuzz_threshold,
                        embed_threshold=embed_threshold)
        if m is None:
            continue
        _, matched_field, score, _ = m
        if matched_field == field:
            candidates.append((k, score))
            return v  # first hit wins; future improvement: take best score
    return None


def _strip_year_suffix(label: str) -> str:
    """'EK pr. 31.12.2024 Aksjekapital' -> 'EK pr. 31.12 Aksjekapital'
    'Lønn 2024' -> 'Lønn'"""
    import re
    s = re.sub(r"\b20[0-2]\d\b", "", label)
    s = re.sub(r"\s+", " ", s).strip()
    return s

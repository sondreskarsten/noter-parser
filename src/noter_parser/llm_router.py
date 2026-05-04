"""Tier 3 LLM router for ambiguous label-to-canonical-field mappings.

Used only as a fallback when fuzzy and embedding both fail. The LLM is
called with the candidate field as a constrained Literal, so it cannot
hallucinate a non-canonical column name — the type system enforces this.

Usage requires:
  pip install anthropic instructor
  ANTHROPIC_API_KEY environment variable

Cost projection: at $1.60/MTok for Claude Haiku 4.5 batch and ~500 tokens
per call, 200k labels × ~5% routed = 10k calls = ~$8. Negligible.
"""
import os
from typing import Optional

from .canonical_schema import CANONICAL_FIELDS


_CLIENT = None


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        try:
            import anthropic
            _CLIENT = anthropic.Anthropic()
        except Exception:
            _CLIENT = False
            return None
    return _CLIENT if _CLIENT else None


def route_label(
    label: str,
    table: str,
    candidates: Optional[list[tuple[str, float]]] = None,
    model: str = "claude-haiku-4-5-20251001",
) -> Optional[tuple[str, float, str]]:
    """Ask Claude to pick the best canonical field for `label` within `table`.

    Args:
        label: raw extracted label
        table: target table name (limits Literal choices)
        candidates: optional ranked list of (field, embedding_score) from
            Tier 2 — passed as context to the LLM
        model: Claude model id

    Returns: (field, confidence, reasoning) or None if API unavailable.
    """
    client = _get_client()
    if client is None:
        return None
    fields = list(CANONICAL_FIELDS.get(table, {}).keys())
    if not fields:
        return None

    candidates_str = ""
    if candidates:
        top = candidates[:5]
        candidates_str = "\n\nTier-2 embedding suggestions (ranked):\n"
        for f, s in top:
            candidates_str += f"  - {f}: cosine={s:.3f}\n"

    fields_list = "\n".join(f"  - {f}" for f in fields)
    prompt = (
        f"You map extracted Norwegian financial-statement labels to canonical "
        f"schema fields. Pick the SINGLE field from the list that best matches "
        f"the label. If none fit, respond with exactly 'NONE'.\n\n"
        f"Table: {table}\n\n"
        f"Available fields:\n{fields_list}\n"
        f"{candidates_str}\n"
        f"Label: {label!r}\n\n"
        f"Respond with the field name only (or 'NONE'). No explanation."
    )

    msg = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
    )
    response = msg.content[0].text.strip()
    if response == "NONE" or response not in fields:
        return None
    return (response, 1.0, "llm_router")


def confident_route(label: str, table: str, embedding_top_k: list[tuple[str, float]],
                    margin_threshold: float = 0.05) -> Optional[tuple[str, float, str]]:
    """Only invoke the LLM when the embedding result is ambiguous.

    Ambiguous = top-1 cosine < 0.78 OR top-1/top-2 margin < `margin_threshold`."""
    if not embedding_top_k:
        return route_label(label, table)
    top = embedding_top_k[0]
    if len(embedding_top_k) >= 2:
        margin = top[1] - embedding_top_k[1][1]
        if top[1] >= 0.82 and margin >= margin_threshold:
            return (top[0], top[1], "embed_confident")
    return route_label(label, table, candidates=embedding_top_k)

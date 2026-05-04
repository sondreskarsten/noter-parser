"""Direct parent extraction. Notes vary across decades:
  - 2010: anchor + name immediately
  - 2011-2013, 2017: anchor + column headers + name + numbers
  - 2018+: 'Eierstruktur' anchor (no 'Eneste aksjonær' phrase)

Primary strategy: parse compound `raw_amounts` keys like 'Pelagia AS Antall aksjer'.
Fallback: regex over `raw_text`.
"""
import re
from typing import Optional

from ..matchers import get_note


_KEY_SUFFIXES = (
    "Antall aksjer", "Antall", "Aksjer", "Sum", "Eier- og stemmeandel",
    "Eier- og", "Eier-andel", "Eier-", "Eierandel",
    "Stemme- andel", "Stemmeandel", "Stemme-",
)


def _from_keys(note: Optional[dict]) -> Optional[str]:
    if not note:
        return None
    candidates: dict[str, int] = {}
    for k in note.get("raw_amounts", {}):
        for suf in _KEY_SUFFIXES:
            if k.endswith(" " + suf):
                name = k[: -(len(suf) + 1)].strip()
                low = name.lower()
                if name and not low.startswith(("ordinære", "sum", "antall")):
                    candidates[name] = candidates.get(name, 0) + 1
                break
    if not candidates:
        return None
    return max(candidates.items(), key=lambda kv: kv[1])[0]


_COL_HEADER = re.compile(
    r"^(Antall(?:\s+aksjer(?:\s+stemmeandel)?)?|Aksjer|"
    r"Sum(?:\s+aksjer)?|Pålydende|Bokført|"
    r"Eier-?\s*og(?:\s+stemmeandel)?|Eier-?\s*andel|"
    r"Eier-?|Stemme-?\s*andel|Stemme-?|andel|stemme[a-zæøå-]*|"
    r"Eierstruktur(?:\s+per[^\n]*)?|"
    r"Eneste aksjon[æa]r[^\n]*|"
    r"Sum (?:eiere|elere)|Sum øvrige|Totalt antall aksjer|"
    r"Aksjekapital(?:en)?[^\n]*)\s*$",
    re.IGNORECASE,
)
_NUMERIC = re.compile(r"^[\d\s,.\-%]+$")


def _from_text(text: str) -> Optional[str]:
    if not text:
        return None
    for anchor_pat in [
        r"Eneste aksjon[æa]r[^\n]*er[\.\:][\s]*\n",
        r"Eierstruktur(?:\s+per[^\n]*)?\n",
    ]:
        m = re.search(anchor_pat, text, re.IGNORECASE)
        if not m:
            continue
        after = text[m.end():]
        konsern_idx = after.find("utarbeider konsernregnskap")
        if konsern_idx > 0:
            after = after[:konsern_idx]
        lines = [ln.strip() for ln in after.split("\n") if ln.strip()]
        name_parts = []
        for ln in lines[:12]:
            if _COL_HEADER.match(ln) or _NUMERIC.match(ln):
                if name_parts:
                    break
                continue
            name_parts.append(ln)
            if len(name_parts) >= 2 and any("AS" in p for p in name_parts):
                break
        if name_parts:
            cand = re.sub(r"\s+", " ", " ".join(name_parts)).strip(" .,:")
            if cand and len(cand) < 80:
                return cand
    return None


def parse_aksjonaer(note: Optional[dict]) -> Optional[str]:
    if not note:
        return None
    return _from_keys(note) or _from_text(note.get("raw_text", "") or "")


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    note = get_note(data, r"aksjekapital.*aksjonær", r"aksjekapital og aksjon")
    if not note:
        return []
    name = parse_aksjonaer(note)
    # Antall aksjer comes from the same compound key that gave us the name
    antall = None
    if name:
        for k, v in note.get("raw_amounts", {}).items():
            if k.startswith(name + " ") and ("aksjer" in k.lower() or k.endswith(" Antall")):
                antall = v
                break
    return [{
        "orgnr": orgnr,
        "report_year": year,
        "source_filing_year": year,
        "aksjonaer_idx": 1,
        "navn": name or "UNKNOWN",
        "antall_aksjer": antall,
        "eierandel_pct": 100.0,
        "verv": None,
        "eid_av_person": False,
    }]

"""Related-party credit flows. Pulls from:
  - Annen langsiktig gjeld (long-term debt to parent)
  - Konserninterne forhold / Transaksjoner og mellomværende med nærstående parter
  - Egenkapital note (konsernbidrag flows)

Direction enum:
  - long_term_debt
  - intercompany_receivable / intercompany_payable
  - intercompany_payable_short
  - intercompany_sales / raw_material_purchase / other_opcost_with_related
  - interest_income_related / interest_expense_related
  - konsernkonto_net_debt / konsernkonto_net_deposit
  - konsernbidrag_received / konsernbidrag_paid
  - konsernbidrag_received_ek / konsernbidrag_paid_ek
"""
import re
from ..matchers import get_note, get_amount


def _classify_party(name: str) -> str:
    if not name or name == "Unknown":
        return "konsernselskap"
    low = name.lower()
    if "pelagia" in low or "epax holding" in low:
        return "morselskap"
    return "konsernselskap"


def build(data: dict, orgnr: str, year: int) -> list[dict]:
    rows = []

    # 1) Long-term debt to parent
    note_lt = get_note(data, r"annen langsiktig gjeld")
    if note_lt:
        for k, v in note_lt.get("raw_amounts", {}).items():
            if "konsernselskap" in k.lower() or "rselskap" in k.lower():
                if str(year) in k:
                    party_match = re.search(
                        r"[Gg]jeld konsernselskap[\s-]*([A-ZÆØÅ][^\n0-9]+?)(?=\s*\d{4}|$)",
                        k,
                    )
                    party = party_match.group(1).strip() if party_match else "Konsernselskap"
                    rate = get_amount(
                        note_lt,
                        r"rente p\.?a\.?",
                        r"^Rente p\.a\.?$",
                        r"rentebærende med:",
                    )
                    forfall = None
                    text = note_lt.get("raw_text", "") or ""
                    m_f = re.search(
                        r"forfall(?:er)?(?:[\w\s,]*)?(\d{1,2}\.\d{1,2}\.\d{4})",
                        text,
                    )
                    if m_f:
                        forfall = m_f.group(1)
                    rows.append({
                        "orgnr": orgnr,
                        "report_year": year,
                        "source_filing_year": year,
                        "party_role": "morselskap",
                        "party_name": party,
                        "direction": "long_term_debt",
                        "amount": v,
                        "interest_rate": rate,
                        "forfall": forfall,
                        "narrative": k,
                    })

    # 2) Konsernforhold / nærstående transactions
    note_kt = get_note(
        data,
        r"konserninterne forhold",
        r"transaksjoner og mellomværende",
        r"nærstående part",
        r"konsern,? tilknyttet selskap",
        r"mellomværende.*konsern",
        r"mellomværende.*nærstående",
        r"^konsernregnskap$",
    )
    if note_kt:
        for k, v in note_kt.get("raw_amounts", {}).items():
            if not isinstance(v, (int, float)):
                continue
            if str(year) not in k:
                continue
            kl = k.lower()
            if "salgsinntekt" in kl:
                direction = "intercompany_sales"
            elif "innkjøp råvarer" in kl or "varekostnad" in kl:
                direction = "raw_material_purchase"
            elif "annen driftskostnad" in kl:
                direction = "other_opcost_with_related"
            elif "renteinntekt" in kl or "renter av" in kl or "renter konsernkonto" in kl:
                direction = "interest_income_related"
            elif "rentekostnad" in kl:
                direction = "interest_expense_related"
            elif "kortsiktig konsern" in kl or "konsernkonto" in kl:
                direction = "konsernkonto_net_debt" if v > 0 else "konsernkonto_net_deposit"
            elif "konsernintern fordring" in kl or ("fordring" in kl and "konsern" in kl):
                direction = "intercompany_receivable"
            elif "konsernintern gjeld" in kl or "konsemintern gjeld" in kl:
                if "langsiktig" in kl:
                    continue
                direction = "intercompany_payable"
            elif "konsernbidrag mottatt" in kl:
                direction = "konsernbidrag_received"
            elif (
                "konsernbidrag avgitt" in kl
                or "konsernbidrag avsatt" in kl
                or "avsatte konsernbidrag" in kl
            ):
                direction = "konsernbidrag_paid"
            elif "leverandørgjeld" in kl and "konsern" in kl:
                direction = "intercompany_payable_short"
            elif re.search(rf"\b(?:pr\.?|per)\s+3?1\.12\.{year}\b", k, re.IGNORECASE):
                # SME pattern: '<Party> PR 31.12.YEAR' = intercompany balance
                direction = "intercompany_balance"
            else:
                continue
            party_match = re.search(
                r"(Pelagia AS|Pelagia Holding AS|FMC Corporation|FMC Biopolymer|"
                r"FMC Health & Nutrition US|FMC Holding Norway AS|FMC Norway Holding AS|"
                r"Epax Pharma UK Ltd|Epax Holding AS|Epax Nutra Holding AS|"
                r"Øvrige FMC[\w\s-]*)",
                k,
            )
            if party_match:
                party = party_match.group(1).strip()
            else:
                # Generic SME pattern: 'NAME PR DATE' or 'NAME 31.12.YEAR'
                generic = re.match(
                    r"^([A-ZÆØÅ][^\d]{2,60}?)(?:\s+(?:PR\.?|per|pr\.))?\s+3?1\.12\.\d{2,4}",
                    k,
                )
                party = generic.group(1).strip() if generic else "Unknown"
            rows.append({
                "orgnr": orgnr,
                "report_year": year,
                "source_filing_year": year,
                "party_role": _classify_party(party),
                "party_name": party,
                "direction": direction,
                "amount": v,
                "interest_rate": None,
                "forfall": None,
                "narrative": k,
            })

    # 3) Konsernbidrag flows from EK note
    note_ek = get_note(data, r"^egenkapital$")
    if note_ek:
        for k, v in note_ek.get("raw_amounts", {}).items():
            if not isinstance(v, (int, float)) or v == 0:
                continue
            kl = k.lower()
            if "konsernbidrag mottatt" in kl and "sum" in kl:
                rows.append({
                    "orgnr": orgnr,
                    "report_year": year,
                    "source_filing_year": year,
                    "party_role": "morselskap",
                    "party_name": None,
                    "direction": "konsernbidrag_received_ek",
                    "amount": v,
                    "interest_rate": None,
                    "forfall": None,
                    "narrative": f"From EK note: {k}",
                })
            elif (
                ("konsernbidrag avgitt" in kl or "konsernbidrag avsatt" in kl)
                and "sum" in kl
            ):
                rows.append({
                    "orgnr": orgnr,
                    "report_year": year,
                    "source_filing_year": year,
                    "party_role": "morselskap",
                    "party_name": None,
                    "direction": "konsernbidrag_paid_ek",
                    "amount": v,
                    "interest_rate": None,
                    "forfall": None,
                    "narrative": f"From EK note: {k}",
                })

    return rows

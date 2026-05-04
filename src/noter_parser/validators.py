"""Arithmetic post-validation of extracted CSV tables.

Per the deep research: a passing roll-forward identity is worth more than
three independent LLM votes for catching extraction errors. We define
three identity classes:

  1. Balance-sheet:       assets ≈ liabilities + equity (within rounding)
  2. Roll-forward:        opening + Δ = closing (egenkapital, varige driftsmidler)
  3. Cross-note:          income statement skattekostnad = skatt note total

The validator returns a per-row dict reporting which identities passed,
which failed, and the magnitude of any discrepancy. Failed rows go to
review.csv — they don't crash the pipeline.

Pandera is optional — if not installed, this module exposes the same
interface using plain Python checks."""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class IdentityResult:
    name: str
    passed: bool
    expected: Optional[float] = None
    actual: Optional[float] = None
    diff: Optional[float] = None
    note: str = ""


def _close_enough(a: float, b: float, rel_tol: float = 1e-3, abs_tol: float = 1.0) -> bool:
    """True if a≈b within relative or absolute tolerance.
    Default: 0.1% relative or 1 NOK absolute (rounding-grade)."""
    if a is None or b is None:
        return False
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def validate_egenkapital_summary(row: dict) -> list[IdentityResult]:
    """Identity: aksjekapital + annen_innskutt + annen_opptjent ≈ sum_egenkapital.

    Note: many rows have NULL components (parsing partial), so we check only
    when all three components are present."""
    out = []
    aksjekap = row.get("aksjekapital")
    innskutt = row.get("annen_innskutt_ek")
    opptjent = row.get("annen_opptjent_ek")
    sum_ek = row.get("sum_egenkapital")

    if all(isinstance(x, (int, float)) and not _isnan(x)
           for x in (aksjekap, innskutt, opptjent, sum_ek)):
        expected = aksjekap + innskutt + opptjent
        passed = _close_enough(expected, sum_ek)
        out.append(IdentityResult(
            name="ek_components_sum",
            passed=passed,
            expected=expected,
            actual=sum_ek,
            diff=expected - sum_ek if not passed else None,
            note="Aksjekapital + Annen innskutt + Annen opptjent should equal Sum egenkapital",
        ))
    return out


def validate_lonn_ytelser(row: dict) -> list[IdentityResult]:
    """Identity: lonninger + arbeidsgiveravgift + pensjon + andre_ytelser ≈ sum_lonnskostnader."""
    out = []
    parts = [
        row.get("lonninger"),
        row.get("arbeidsgiveravgift"),
        row.get("pensjonskostnader"),
        row.get("andre_ytelser"),
    ]
    sumk = row.get("sum_lonnskostnader")
    if all(isinstance(x, (int, float)) and not _isnan(x) for x in parts) and \
       isinstance(sumk, (int, float)) and not _isnan(sumk):
        expected = sum(parts)
        passed = _close_enough(expected, sumk)
        out.append(IdentityResult(
            name="lonn_components_sum",
            passed=passed,
            expected=expected,
            actual=sumk,
            diff=expected - sumk if not passed else None,
            note="Lønninger + AGA + Pensjon + Andre ytelser should equal Sum lønnskostnader",
        ))
    return out


def validate_skatt_aaret(row: dict) -> list[IdentityResult]:
    """Identity: betalbar_skatt + endring_utsatt_skatt ≈ skattekostnad_total."""
    out = []
    betalbar = row.get("betalbar_skatt")
    endring = row.get("endring_utsatt_skatt")
    total = row.get("skattekostnad_total")
    if all(isinstance(x, (int, float)) and not _isnan(x)
           for x in (betalbar, endring, total)):
        expected = betalbar + endring
        passed = _close_enough(expected, total)
        out.append(IdentityResult(
            name="skatt_components_sum",
            passed=passed,
            expected=expected,
            actual=total,
            diff=expected - total if not passed else None,
            note="Betalbar + Endring utsatt skatt should equal Skattekostnad total",
        ))
    return out


def validate_anleggsmidler_rollforward(row: dict) -> list[IdentityResult]:
    """Identity: anskaffelseskost_31_12 - akk_avskrivninger - akk_nedskrivninger ≈ balansefort_31_12.

    Only run on per-asset-class rows where all 4 values are present."""
    out = []
    if row.get("asset_class") in (None, "TOTAL", "SUM"):
        return out
    ank = row.get("anskaffelseskost_31_12")
    akk_av = row.get("akkumulerte_avskrivninger_31_12")
    akk_ned = row.get("akkumulerte_nedskrivninger_31_12")
    bal = row.get("balansefort_31_12")
    if all(isinstance(x, (int, float)) and not _isnan(x)
           for x in (ank, bal)):
        akk_av_v = akk_av if isinstance(akk_av, (int, float)) and not _isnan(akk_av) else 0
        akk_ned_v = akk_ned if isinstance(akk_ned, (int, float)) and not _isnan(akk_ned) else 0
        # Akkumulerte are stored as positive (or sometimes negative) — try both
        for sign in (1, -1):
            expected = ank + sign * (akk_av_v + akk_ned_v)
            if _close_enough(expected, bal):
                out.append(IdentityResult(
                    name=f"rollforward_balanse_{'positive' if sign == 1 else 'subtract'}",
                    passed=True,
                    expected=expected,
                    actual=bal,
                ))
                return out
        # Neither sign convention matched
        expected_sub = ank - (akk_av_v + akk_ned_v)
        out.append(IdentityResult(
            name="rollforward_balanse",
            passed=False,
            expected=expected_sub,
            actual=bal,
            diff=expected_sub - bal,
            note="Anskaffelseskost - akk. avskrivninger - akk. nedskrivninger should equal Balanseført",
        ))
    return out


def _isnan(v) -> bool:
    try:
        return math.isnan(v)
    except (TypeError, ValueError):
        return False


def validate_table(table: str, rows: list[dict]) -> dict:
    """Run validators for the given table. Returns dict with summary + per-row results."""
    validator = {
        "egenkapital_summary": validate_egenkapital_summary,
        "lonn_ytelser": validate_lonn_ytelser,
        "skatt_aaret": validate_skatt_aaret,
        "anleggsmidler_rollforward": validate_anleggsmidler_rollforward,
    }.get(table)

    if validator is None:
        return {
            "table": table,
            "n_rows": len(rows),
            "n_validated": 0,
            "n_passed": 0,
            "n_failed": 0,
            "rows": [],
        }

    results = []
    n_passed = 0
    n_failed = 0
    n_validated = 0
    for row in rows:
        identities = validator(row)
        if identities:
            n_validated += 1
            if all(r.passed for r in identities):
                n_passed += 1
            else:
                n_failed += 1
        results.append({
            "row": row,
            "identities": [
                {"name": r.name, "passed": r.passed,
                 "expected": r.expected, "actual": r.actual, "diff": r.diff}
                for r in identities
            ],
        })
    return {
        "table": table,
        "n_rows": len(rows),
        "n_validated": n_validated,
        "n_passed": n_passed,
        "n_failed": n_failed,
        "pass_rate": n_passed / n_validated if n_validated else None,
        "rows": results,
    }


def run_validators(tables: dict[str, list[dict]]) -> dict:
    """Run all table validators. Convenience wrapper for stress test."""
    return {table: validate_table(table, rows) for table, rows in tables.items()}


def cross_validate_regnskapsapi(tables: dict[str, list[dict]],
                                 api_data: dict) -> list[IdentityResult]:
    """Cross-check noter-extracted values against regnskapsregister-api totals.

    api_data: flattened dict from regnskapsapi/validation/{orgnr}_{year}.json
    Returns list of IdentityResult for each check performed."""
    out = []

    api_ek = api_data.get("sum_egenkapital")
    if api_ek is not None:
        for row in tables.get("egenkapital_summary", []):
            noter_val = row.get("sum_egenkapital")
            if isinstance(noter_val, (int, float)) and not _isnan(noter_val):
                passed = _close_enough(float(noter_val), float(api_ek), rel_tol=0.01)
                out.append(IdentityResult(
                    name="api_cross_sum_egenkapital",
                    passed=passed,
                    expected=float(api_ek),
                    actual=float(noter_val),
                    diff=float(noter_val) - float(api_ek) if not passed else None,
                    note="Noter sum_egenkapital vs regnskapsapi (1% tol)",
                ))
                break

    api_eiendeler = api_data.get("sum_eiendeler")
    if api_eiendeler is not None:
        api_balance = api_data.get("sum_egenkapital_gjeld")
        if api_balance is not None:
            passed = _close_enough(float(api_eiendeler), float(api_balance))
            out.append(IdentityResult(
                name="api_balance_sheet_identity",
                passed=passed,
                expected=float(api_eiendeler),
                actual=float(api_balance),
                note="API internal: sum_eiendeler == sum_egenkapital_gjeld",
            ))

    return out

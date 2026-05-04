"""Regression tests against EPAX 2024 fixture. These pin the EPAX 2024
extraction to known-good values; if a parser change drops a row or changes
a number, these will fail."""
import json
from pathlib import Path

import pytest

from noter_parser import parse_one

FIXTURE = Path(__file__).parent / "fixtures" / "989100106_2024.json"


@pytest.fixture(scope="module")
def epax_2024_tables():
    data = json.loads(FIXTURE.read_text())
    return parse_one(data, "989100106", 2024)


def test_documents_one_row(epax_2024_tables):
    rows = epax_2024_tables["documents"]
    assert len(rows) == 1
    assert rows[0]["n_notes_extracted"] == 20
    assert rows[0]["report_year"] == 2024


def test_aksjonaer_pelagia(epax_2024_tables):
    rows = epax_2024_tables["aksjonaerer"]
    assert len(rows) == 1
    assert rows[0]["navn"] == "Pelagia AS"


def test_egenkapital_2024(epax_2024_tables):
    rows = epax_2024_tables["egenkapital_summary"]
    assert len(rows) == 1
    assert rows[0]["sum_egenkapital"] == 449542025
    assert rows[0]["aksjekapital"] == 3814654


def test_lonn_2024(epax_2024_tables):
    rows = epax_2024_tables["lonn_ytelser"]
    assert len(rows) == 1
    assert rows[0]["lonninger"] == 64957239
    assert rows[0]["arsverk"] == 71


def test_bankinnskudd_text_fallback(epax_2024_tables):
    """Note 14 is prose-only — extracted via raw_text fallback."""
    rows = epax_2024_tables["bankinnskudd_bundne"]
    assert len(rows) == 1
    assert rows[0]["bundne_skattetrekksmidler"] == 2910050


def test_long_term_debt_to_pelagia(epax_2024_tables):
    rows = epax_2024_tables["relatert_part_kreditt"]
    debt = [r for r in rows if r["direction"] == "long_term_debt"]
    assert any(r["amount"] == 522504331 for r in debt)


def test_konsernkonto_explosion_2024(epax_2024_tables):
    rows = epax_2024_tables["relatert_part_kreditt"]
    konto = [r for r in rows if r["direction"] == "konsernkonto_net_debt"]
    assert any(r["amount"] == 482326029 for r in konto)


def test_skattefunn_positive_2024(epax_2024_tables):
    rows = epax_2024_tables["skattefunn"]
    assert len(rows) == 1
    # 2.2 mNOK fordring — must be positive (skill-bug 'fordring SkatteFUNN' negative-sign issue)
    assert rows[0]["forventet_tilskudd_nok"] == 2200000


def test_lawsuit_2024(epax_2024_tables):
    rows = epax_2024_tables["kontingente_forpliktelser"]
    assert len(rows) == 1
    assert rows[0]["amount_nok"] == 53000000
    assert rows[0]["appealed"] is True


def test_anleggsmidler_2024_capex(epax_2024_tables):
    rows = epax_2024_tables["anleggsmidler_rollforward"]
    aue = [r for r in rows if r["asset_class"] == "Anlegg under utførelse"]
    assert any(r["balansefort_31_12"] == 65568384 for r in aue)

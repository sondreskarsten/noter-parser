"""Tests for the schema-matching cascade and validators."""
import pytest

from noter_parser import canonical_schema, schema_mapper, validators


class TestCanonicalSchema:
    def test_egenkapital_summary_has_sum(self):
        fields = canonical_schema.all_fields("egenkapital_summary")
        assert "sum_egenkapital" in fields
        assert "aksjekapital" in fields
        assert "annen_innskutt_ek" in fields

    def test_synonyms_for_known_field(self):
        syns = canonical_schema.synonyms_for("egenkapital_summary", "annen_innskutt_ek")
        assert "Annen innskutt egenkapital" in syns
        assert "Overkurs" in syns

    def test_unknown_table_returns_empty(self):
        assert canonical_schema.synonyms_for("nonexistent_table", "x") == []

    def test_all_synonyms_flat(self):
        all_s = canonical_schema.all_synonyms_flat()
        assert all(len(t) == 3 for t in all_s)
        # Spot check: at least one entry per defined table
        tables = {t[0] for t in all_s}
        assert "egenkapital_summary" in tables
        assert "lonn_ytelser" in tables


class TestFuzzyMatch:
    def test_exact_match_canonical(self):
        m = schema_mapper.fuzzy_match("Sum egenkapital", table_filter="egenkapital_summary")
        assert m is not None
        table, field, score = m
        assert field == "sum_egenkapital"
        assert score >= 95

    def test_synonym_match_overkurs(self):
        m = schema_mapper.fuzzy_match("Overkurs", table_filter="egenkapital_summary")
        assert m is not None
        assert m[1] == "annen_innskutt_ek"

    def test_norwegian_alt_spelling(self):
        m = schema_mapper.fuzzy_match("Aksje-kapital", table_filter="egenkapital_summary")
        assert m is not None
        assert m[1] == "aksjekapital"

    def test_no_match_below_threshold(self):
        # Garbage shouldn't match anything at WRatio>=95
        m = schema_mapper.fuzzy_match("xyz random garbage 9999", threshold=95)
        assert m is None

    def test_table_filter_isolates(self):
        # 'Sum' alone is too generic but with filter should match the right field
        m = schema_mapper.fuzzy_match(
            "Sum lønnskostnader", table_filter="lonn_ytelser"
        )
        assert m is not None
        assert m[1] == "sum_lonnskostnader"


class TestFindInAmounts:
    def test_overkurs_routes_to_innskutt(self):
        # SME label 'Overkurs Pr. 31.12.2025' - reg miss; mapper should find via synonym
        amounts = {"Overkurs Pr. 31.12.2025": 6447671.0}
        val = schema_mapper.find_in_amounts(
            amounts, "egenkapital_summary", "annen_innskutt_ek", year=2025
        )
        assert val == 6447671.0

    def test_year_filter_excludes_other_years(self):
        amounts = {
            "Overkurs Pr. 31.12.2024": 1000.0,
            "Overkurs Pr. 31.12.2025": 2000.0,
        }
        v = schema_mapper.find_in_amounts(
            amounts, "egenkapital_summary", "annen_innskutt_ek", year=2025
        )
        assert v == 2000.0


class TestValidatorsEgenkapital:
    def test_balanced_components(self):
        row = {
            "aksjekapital": 100000.0,
            "annen_innskutt_ek": 200000.0,
            "annen_opptjent_ek": 500000.0,
            "sum_egenkapital": 800000.0,
        }
        results = validators.validate_egenkapital_summary(row)
        assert len(results) == 1
        assert results[0].passed is True

    def test_unbalanced_components(self):
        row = {
            "aksjekapital": 100000.0,
            "annen_innskutt_ek": 200000.0,
            "annen_opptjent_ek": 500000.0,
            "sum_egenkapital": 999999.0,  # wrong
        }
        results = validators.validate_egenkapital_summary(row)
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].diff is not None

    def test_missing_components_no_check(self):
        # When components are NaN/None, skip the identity check (don't fail)
        row = {
            "aksjekapital": 100000.0,
            "annen_innskutt_ek": None,
            "annen_opptjent_ek": 500000.0,
            "sum_egenkapital": 800000.0,
        }
        results = validators.validate_egenkapital_summary(row)
        assert len(results) == 0  # no identity could be checked


class TestValidatorsSkatt:
    def test_skatt_balanced(self):
        row = {
            "betalbar_skatt": 200000.0,
            "endring_utsatt_skatt": 50000.0,
            "skattekostnad_total": 250000.0,
        }
        results = validators.validate_skatt_aaret(row)
        assert len(results) == 1
        assert results[0].passed is True

    def test_skatt_unbalanced(self):
        row = {
            "betalbar_skatt": 200000.0,
            "endring_utsatt_skatt": 50000.0,
            "skattekostnad_total": 999999.0,
        }
        results = validators.validate_skatt_aaret(row)
        assert results[0].passed is False


class TestValidateTable:
    def test_summary_aggregation(self):
        rows = [
            {"aksjekapital": 100, "annen_innskutt_ek": 200, "annen_opptjent_ek": 300, "sum_egenkapital": 600},
            {"aksjekapital": 100, "annen_innskutt_ek": 200, "annen_opptjent_ek": 300, "sum_egenkapital": 999},  # bad
            {"aksjekapital": 100, "annen_innskutt_ek": None, "annen_opptjent_ek": 300, "sum_egenkapital": 600},  # incomplete
        ]
        report = validators.validate_table("egenkapital_summary", rows)
        assert report["n_rows"] == 3
        assert report["n_validated"] == 2
        assert report["n_passed"] == 1
        assert report["n_failed"] == 1

    def test_unknown_table_returns_zero_validated(self):
        report = validators.validate_table("aksjonaerer", [{"navn": "X"}])
        assert report["n_validated"] == 0

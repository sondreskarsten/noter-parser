"""Tests for canonical_schema, schema_mapper (fuzzy tier only — embedding
tier requires sentence-transformers and is verified at runtime), and validators."""
from noter_parser import canonical_schema, schema_mapper, validators


class TestCanonicalSchema:
    def test_egenkapital_summary_has_required_fields(self):
        fields = canonical_schema.all_fields("egenkapital_summary")
        assert "sum_egenkapital" in fields
        assert "aksjekapital" in fields
        assert "annen_innskutt_ek" in fields
        assert "annen_opptjent_ek" in fields

    def test_synonyms_for_returns_list(self):
        syns = canonical_schema.synonyms_for("egenkapital_summary", "aksjekapital")
        assert isinstance(syns, list)
        assert any("Aksjekapital" in s for s in syns)

    def test_unknown_table_returns_empty(self):
        assert canonical_schema.all_fields("nonexistent_table") == []
        assert canonical_schema.synonyms_for("foo", "bar") == []

    def test_all_synonyms_flat_returns_tuples(self):
        flat = canonical_schema.all_synonyms_flat()
        assert len(flat) > 50
        # Each entry is (table, field, synonym)
        for entry in flat[:5]:
            assert len(entry) == 3
            assert all(isinstance(x, str) for x in entry)


class TestSchemaMapperFuzzy:
    def test_exact_match_high_score(self):
        result = schema_mapper.fuzzy_match("Aksjekapital", table_filter="egenkapital_summary")
        assert result is not None
        table, field, score = result
        assert table == "egenkapital_summary"
        assert field == "aksjekapital"
        assert score >= 95

    def test_typo_handled(self):
        # WRatio handles small typos
        result = schema_mapper.fuzzy_match("Aksjekapittal", table_filter="egenkapital_summary")
        if result:
            table, field, score = result
            assert field == "aksjekapital"

    def test_no_match_returns_none(self):
        result = schema_mapper.fuzzy_match("zzzz unrelated text", threshold=95)
        assert result is None

    def test_table_filter_works(self):
        # 'Skattepliktig inntekt' should not match in egenkapital_summary
        result = schema_mapper.fuzzy_match("Skattepliktig inntekt",
                                          table_filter="egenkapital_summary",
                                          threshold=95)
        assert result is None

    def test_strip_year_suffix(self):
        assert schema_mapper._strip_year_suffix("Aksjekapital 2024") == "Aksjekapital"
        assert schema_mapper._strip_year_suffix("EK pr. 31.12.2024 Sum") == "EK pr. 31.12. Sum"
        assert schema_mapper._strip_year_suffix("Lønninger") == "Lønninger"


class TestSchemaMapperFindInAmounts:
    def test_finds_match_in_dict(self):
        amounts = {
            "Aksjekapital 2024": 1000000,
            "Annen opptjent egenkapital 2024": 500000,
        }
        v = schema_mapper.find_in_amounts(amounts, "egenkapital_summary",
                                          "aksjekapital", year=2024)
        assert v == 1000000

    def test_year_filter(self):
        amounts = {
            "Aksjekapital 2023": 800000,
            "Aksjekapital 2024": 1000000,
        }
        v = schema_mapper.find_in_amounts(amounts, "egenkapital_summary",
                                          "aksjekapital", year=2024)
        assert v == 1000000

    def test_no_match_returns_none(self):
        amounts = {"foobar": 12345}
        v = schema_mapper.find_in_amounts(amounts, "egenkapital_summary",
                                          "aksjekapital")
        assert v is None


class TestValidatorsEgenkapital:
    def test_pass_when_components_sum(self):
        row = {
            "aksjekapital": 100,
            "annen_innskutt_ek": 200,
            "annen_opptjent_ek": 300,
            "sum_egenkapital": 600,
        }
        results = validators.validate_egenkapital_summary(row)
        assert len(results) == 1
        assert results[0].passed

    def test_fail_when_components_dont_sum(self):
        row = {
            "aksjekapital": 100,
            "annen_innskutt_ek": 200,
            "annen_opptjent_ek": 300,
            "sum_egenkapital": 999,
        }
        results = validators.validate_egenkapital_summary(row)
        assert len(results) == 1
        assert not results[0].passed
        assert results[0].diff == -399

    def test_skip_when_partial(self):
        row = {"aksjekapital": 100, "sum_egenkapital": None}
        results = validators.validate_egenkapital_summary(row)
        assert results == []

    def test_rounding_tolerance(self):
        # Off by 0.1 NOK on 1B sum — should pass
        row = {
            "aksjekapital": 1_000_000_000.0,
            "annen_innskutt_ek": 0,
            "annen_opptjent_ek": 0,
            "sum_egenkapital": 1_000_000_000.1,
        }
        results = validators.validate_egenkapital_summary(row)
        assert results[0].passed


class TestValidatorsLonn:
    def test_pass(self):
        row = {
            "lonninger": 1000,
            "arbeidsgiveravgift": 100,
            "pensjonskostnader": 50,
            "andre_ytelser": 10,
            "sum_lonnskostnader": 1160,
        }
        results = validators.validate_lonn_ytelser(row)
        assert results[0].passed

    def test_fail_with_diff(self):
        row = {
            "lonninger": 1000,
            "arbeidsgiveravgift": 100,
            "pensjonskostnader": 50,
            "andre_ytelser": 10,
            "sum_lonnskostnader": 9999,
        }
        results = validators.validate_lonn_ytelser(row)
        assert not results[0].passed


class TestValidatorsSkatt:
    def test_pass(self):
        row = {
            "betalbar_skatt": 100_000,
            "endring_utsatt_skatt": 20_000,
            "skattekostnad_total": 120_000,
        }
        results = validators.validate_skatt_aaret(row)
        assert results[0].passed


class TestValidateTable:
    def test_summary_keys_present(self):
        rows = [
            {"aksjekapital": 100, "annen_innskutt_ek": 0,
             "annen_opptjent_ek": 0, "sum_egenkapital": 100},
            {"aksjekapital": 200, "annen_innskutt_ek": 0,
             "annen_opptjent_ek": 0, "sum_egenkapital": 999},
        ]
        result = validators.validate_table("egenkapital_summary", rows)
        assert result["n_rows"] == 2
        assert result["n_validated"] == 2
        assert result["n_passed"] == 1
        assert result["n_failed"] == 1
        assert result["pass_rate"] == 0.5

    def test_unknown_table_returns_zero_validations(self):
        result = validators.validate_table("foo", [{"a": 1}])
        assert result["n_validated"] == 0

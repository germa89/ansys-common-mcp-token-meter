"""Tests for scenarios.py."""

from __future__ import annotations

import json

import pytest

from ansys.common.mcp.token_meter.scenarios import DEFAULT_SCENARIOS, load_scenarios


class TestDefaultScenarios:
    def test_default_key_exists(self):
        assert "default" in DEFAULT_SCENARIOS

    def test_default_has_empty_disable_tags(self):
        assert DEFAULT_SCENARIOS["default"]["disable_tags"] == set()


class TestLoadScenarios:
    def test_returns_default_when_no_args(self):
        result = load_scenarios()
        assert "default" in result

    def test_merges_config_dict(self):
        config = {"cold": {"disable_tags": ["slow"], "description": "No slow tools"}}
        result = load_scenarios(config=config)
        assert "cold" in result
        assert "default" in result
        assert result["cold"]["disable_tags"] == {"slow"}

    def test_config_dict_disable_tags_normalized_to_set(self):
        config = {"custom": {"disable_tags": ["a", "b"]}}
        result = load_scenarios(config=config)
        assert isinstance(result["custom"]["disable_tags"], set)

    def test_load_from_json_file(self, tmp_path):
        scenarios_data = {"minimal": {"disable_tags": ["requires_mapdl"], "description": "Minimal"}}
        f = tmp_path / "scenarios.json"
        f.write_text(json.dumps(scenarios_data))
        result = load_scenarios(scenario_file=str(f))
        assert "minimal" in result
        assert result["minimal"]["disable_tags"] == {"requires_mapdl"}

    def test_load_from_toml_file(self, tmp_path):
        toml_content = '[cold]\ndisable_tags = ["slow"]\ndescription = "No slow tools"\n'
        f = tmp_path / "scenarios.toml"
        f.write_text(toml_content)
        result = load_scenarios(scenario_file=str(f))
        assert "cold" in result

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_scenarios(scenario_file="/nonexistent/scenarios.json")

    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "scenarios.yaml"
        f.write_text("cold:\n  disable_tags: [slow]\n")
        with pytest.raises(ValueError, match="Unsupported"):
            load_scenarios(scenario_file=str(f))

    def test_config_and_file_merged(self, tmp_path):
        f = tmp_path / "s.json"
        f.write_text(json.dumps({"from_file": {"disable_tags": []}}))
        result = load_scenarios(config={"from_config": {"disable_tags": []}}, scenario_file=str(f))
        assert "from_file" in result
        assert "from_config" in result
        assert "default" in result

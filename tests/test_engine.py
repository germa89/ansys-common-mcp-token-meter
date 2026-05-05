"""Tests for engine.py."""

from __future__ import annotations

import pytest

from ansys.common.mcp.token_meter.engine import (
    TokenCounter,
    TokenItemReport,
    TokenizerBackend,
    TokenReport,
    count_tokens,
)

# ── count_tokens ───────────────────────────────────────────────────────────────


class TestCountTokens:
    def test_chars_backend(self):
        text = "a" * 100
        assert count_tokens(text, TokenizerBackend.CHARS) == 25

    def test_chars_empty(self):
        assert count_tokens("", TokenizerBackend.CHARS) == 0

    def test_tiktoken_cl100k(self):
        # "hello world" should be 2 tokens with cl100k_base
        result = count_tokens("hello world", TokenizerBackend.CL100K_BASE)
        assert isinstance(result, int)
        assert result > 0

    def test_tiktoken_o200k(self):
        result = count_tokens("hello world", TokenizerBackend.O200K_BASE)
        assert isinstance(result, int)
        assert result > 0

    def test_fallback_on_import_error(self, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "tiktoken", None)
        with pytest.warns(UserWarning, match="tiktoken is not installed"):
            result = count_tokens("hello world", TokenizerBackend.CL100K_BASE)
        assert result == len("hello world") // 4


# ── TokenCounter ───────────────────────────────────────────────────────────────


class TestTokenCounter:
    async def test_build_report_default(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()

        assert isinstance(report, TokenReport)
        assert report.scenario == "default"
        assert report.tokenizer == "chars"
        assert len(report.items) > 0

    async def test_summary_keys(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()

        expected_keys = {
            "tools_enabled",
            "tools_disabled",
            "tools_total",
            "tool_tokens",
            "prompt_tokens",
            "resource_tokens",
            "total_baseline_tokens",
        }
        assert expected_keys == set(report.summary.keys())

    async def test_disable_tags(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report(disable_tags={"optional"})

        disabled = [i for i in report.items if i.status == "disabled"]
        assert len(disabled) > 0
        for item in disabled:
            assert "optional" in item.tags

    async def test_filter_name(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report(filter_name="add")

        assert len(report.items) == 1
        assert report.items[0].name == "add"

    async def test_filter_type_tool(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report(filter_type="tool")

        assert all(i.item_type == "tool" for i in report.items)

    async def test_filter_type_prompt(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report(filter_type="prompt")

        assert all(i.item_type == "prompt" for i in report.items)

    async def test_unknown_scenario_raises(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        with pytest.raises(ValueError, match="Unknown scenario"):
            await counter.build_report(scenario="nonexistent")

    async def test_custom_scenario(self, sample_app):
        scenarios = {"no_optional": {"disable_tags": {"optional"}, "description": "No optional tools"}}
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS, scenarios=scenarios)
        report = await counter.build_report(scenario="no_optional")

        disabled = [i for i in report.items if i.status == "disabled"]
        assert len(disabled) > 0

    async def test_enable_tags_overrides_disable(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        # disable "core", then re-enable by passing enable_tags={"core"}
        report = await counter.build_report(disable_tags={"core"}, enable_tags={"core"})
        disabled = [i for i in report.items if i.status == "disabled" and "core" in i.tags]
        assert disabled == []

    async def test_total_tokens_equals_sum(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        s = report.summary
        assert s["total_baseline_tokens"] == s["tool_tokens"] + s["prompt_tokens"] + s["resource_tokens"]

    async def test_token_item_report_fields(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        for item in report.items:
            assert isinstance(item, TokenItemReport)
            assert item.tokens >= 0
            assert item.characters >= 0

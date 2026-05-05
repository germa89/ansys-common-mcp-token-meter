"""Tests for reporter.py."""

from __future__ import annotations

import json

from ansys.common.mcp.token_meter.engine import TokenCounter, TokenizerBackend
from ansys.common.mcp.token_meter.reporter import format_json, format_table


class TestFormatJson:
    async def test_returns_valid_json(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_json(report)
        data = json.loads(result)
        assert "scenario" in data
        assert "tokenizer" in data
        assert "summary" in data
        assert "tools" in data
        assert "prompts" in data
        assert "resources" in data

    async def test_tool_fields(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        data = json.loads(format_json(report))
        for tool in data["tools"]:
            assert "name" in tool
            assert "status" in tool
            assert "tags" in tool
            assert "tokens" in tool
            assert "characters" in tool

    async def test_prompt_fields(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        data = json.loads(format_json(report))
        for prompt in data["prompts"]:
            assert "name" in prompt
            assert "tokens" in prompt
            assert "characters" in prompt

    async def test_scenario_name_in_output(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        data = json.loads(format_json(report))
        assert data["scenario"] == "default"


class TestFormatTable:
    async def test_returns_string(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_table(report)
        assert isinstance(result, str)

    async def test_contains_title(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_table(report, title="Custom Title")
        assert "Custom Title" in result

    async def test_contains_scenario(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_table(report)
        assert "default" in result

    async def test_contains_summary(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_table(report)
        assert "SUMMARY" in result
        assert "Total baseline" in result

    async def test_contains_tool_names(self, sample_app):
        counter = TokenCounter(sample_app, tokenizer=TokenizerBackend.CHARS)
        report = await counter.build_report()
        result = format_table(report)
        assert "add" in result
        assert "subtract" in result

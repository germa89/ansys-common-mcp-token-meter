"""Tests for pytest_plugin.py."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from ansys.common.mcp.token_meter import TokenizerBackend, token_budget
from ansys.common.mcp.token_meter.pytest_plugin import _run_report

# ── Helpers ────────────────────────────────────────────────────────────────────


def make_app() -> FastMCP:
    """Return a minimal FastMCP app for plugin tests."""
    app = FastMCP(name="plugin-test-app", instructions="Plugin test server")

    @app.tool(tags={"core"})
    def add(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    @app.tool(tags={"optional"})
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    @app.prompt()
    def greeting() -> str:
        """Return a greeting."""
        return "Hello!"

    return app


# ── token_budget decorator ─────────────────────────────────────────────────────


class TestTokenBudgetDecorator:
    def test_sync_test_runs(self, capsys):
        """@token_budget on a sync function runs the test body and prints report."""
        app = make_app()
        ran = []

        @token_budget(app)
        def my_test():
            ran.append(True)

        my_test()

        assert ran == [True]
        out = capsys.readouterr().out
        assert "Token Report" in out

    async def test_async_test_runs(self, capsys):
        """@token_budget on an async function runs the test body and prints report."""
        app = make_app()
        ran = []

        @token_budget(app)
        async def my_async_test():
            ran.append(True)

        await my_async_test()

        assert ran == [True]
        out = capsys.readouterr().out
        assert "Token Report" in out

    async def test_max_tokens_pass(self):
        """Test passes when total tokens are within the budget."""
        app = make_app()

        @token_budget(app, max_tokens=10_000, report_tokens=False)
        async def my_test():
            pass

        await my_test()  # should not raise

    async def test_max_tokens_fail(self):
        """Test raises AssertionError when token budget is exceeded."""
        app = make_app()

        @token_budget(app, max_tokens=1, report_tokens=False)
        async def my_test():
            pass

        with pytest.raises(AssertionError, match="Token budget exceeded"):
            await my_test()

    async def test_report_tokens_false(self, capsys):
        """When report_tokens=False, no report is printed to stdout."""
        app = make_app()

        @token_budget(app, report_tokens=False)
        async def my_test():
            pass

        await my_test()

        out = capsys.readouterr().out
        assert "Token Report" not in out

    async def test_with_disable_tags(self):
        """Disabling a tag reduces enabled tool count in the summary."""
        app = make_app()

        report_all = await _run_report(
            app,
            TokenizerBackend.CL100K_BASE,
            "default",
            disable_tags=None,
            enable_tags=None,
            report_tokens=False,
            max_tokens=None,
        )

        report_disabled = await _run_report(
            app,
            TokenizerBackend.CL100K_BASE,
            "default",
            disable_tags={"optional"},
            enable_tags=None,
            report_tokens=False,
            max_tokens=None,
        )

        assert report_disabled.summary["tools_disabled"] > report_all.summary["tools_disabled"]
        assert report_disabled.summary["tools_enabled"] < report_all.summary["tools_enabled"]

    def test_decorator_preserves_function_name(self):
        """functools.wraps preserves the wrapped function metadata."""
        app = make_app()

        @token_budget(app, report_tokens=False)
        def my_named_test():
            pass

        assert my_named_test.__name__ == "my_named_test"


# ── token_report fixture ───────────────────────────────────────────────────────


class TestTokenReportFixture:
    async def test_returns_report(self, token_report):
        """token_report fixture returns a callable that builds a TokenReport."""
        app = make_app()
        report = await token_report(app)

        assert report.scenario == "default"
        assert isinstance(report.summary, dict)
        expected_keys = {
            "tools_enabled",
            "tools_disabled",
            "tools_total",
            "tool_tokens",
            "prompt_tokens",
            "resource_tokens",
            "total_baseline_tokens",
        }
        assert expected_keys <= set(report.summary.keys())

    async def test_report_has_items(self, token_report):
        """Token report items correspond to app tools and prompts."""
        app = make_app()
        report = await token_report(app)

        tool_items = [i for i in report.items if i.item_type == "tool"]
        prompt_items = [i for i in report.items if i.item_type == "prompt"]

        assert len(tool_items) == 2
        assert len(prompt_items) == 1

    async def test_report_with_disable_tags(self, token_report):
        """token_report fixture supports disable_tags kwarg."""
        app = make_app()
        report = await token_report(app, disable_tags={"core"})

        disabled = [i for i in report.items if i.status == "disabled"]
        assert len(disabled) == 1  # only 'add' has the 'core' tag

    async def test_total_tokens_positive(self, token_report, sample_app):
        """Total baseline tokens for sample_app are positive."""
        report = await token_report(sample_app)
        assert report.summary["total_baseline_tokens"] > 0

    async def test_uses_tokenizer_kwarg(self, token_report):
        """token_report fixture uses CL100K_BASE by default via TokenCounter."""
        app = make_app()
        report = await token_report(app)
        assert report.tokenizer == TokenizerBackend.CL100K_BASE.value


# ── Integration: token_budget used with sample_app fixture ────────────────────


class TestTokenBudgetIntegration:
    async def test_with_sample_app(self, capsys, sample_app):
        """@token_budget works with the shared sample_app fixture."""

        @token_budget(sample_app, report_tokens=True)
        async def my_test():
            pass

        await my_test()

        out = capsys.readouterr().out
        assert "Token Report" in out
        assert "add" in out

    async def test_budget_assertion_message_contains_actual_and_limit(self, sample_app):
        """AssertionError message shows actual tokens and the configured limit."""

        @token_budget(sample_app, max_tokens=1, report_tokens=False)
        async def my_test():
            pass

        with pytest.raises(AssertionError) as exc_info:
            await my_test()

        msg = str(exc_info.value)
        assert "1" in msg  # limit
        assert "tokens" in msg.lower()

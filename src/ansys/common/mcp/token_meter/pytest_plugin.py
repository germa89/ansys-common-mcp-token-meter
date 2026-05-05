"""Pytest plugin: @token_budget decorator and token_report fixture."""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any

import pytest

from ansys.common.mcp.token_meter.engine import TokenCounter, TokenizerBackend, TokenReport


def token_budget(
    app: Any,
    max_tokens: int | None = None,
    tokenizer: TokenizerBackend = TokenizerBackend.CL100K_BASE,
    scenario: str = "default",
    disable_tags: set[str] | None = None,
    enable_tags: set[str] | None = None,
    report_tokens: bool = True,
) -> Any:
    """Decorator that enforces a token budget on a test function.

    After the test body runs, builds a :class:`TokenReport` and optionally
    prints it. When *max_tokens* is set the test fails if the total baseline
    token count exceeds the limit.

    Parameters
    ----------
    app:
        A :class:`fastmcp.FastMCP` application instance.
    max_tokens:
        Maximum allowed total baseline tokens. ``None`` disables the assertion.
    tokenizer:
        Tokenizer backend used for counting.
    scenario:
        Scenario name passed to :meth:`TokenCounter.build_report`.
    disable_tags:
        Tags to disable when building the report.
    enable_tags:
        Tags to re-enable when building the report.
    report_tokens:
        When ``True``, print the formatted token table to stdout.
    """

    def decorator(fn: Any) -> Any:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = await fn(*args, **kwargs)
                await _run_report(app, tokenizer, scenario, disable_tags, enable_tags, report_tokens, max_tokens)
                return result

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)
            asyncio.run(_run_report(app, tokenizer, scenario, disable_tags, enable_tags, report_tokens, max_tokens))
            return result

        return sync_wrapper

    return decorator


async def _run_report(
    app: Any,
    tokenizer: TokenizerBackend,
    scenario: str,
    disable_tags: set[str] | None,
    enable_tags: set[str] | None,
    report_tokens: bool,
    max_tokens: int | None,
) -> TokenReport:
    """Build report, optionally print it, and assert budget."""
    counter = TokenCounter(app, tokenizer)
    report = await counter.build_report(scenario, disable_tags=disable_tags, enable_tags=enable_tags)

    if report_tokens:
        _print_report(report)

    if max_tokens is not None:
        actual = report.summary["total_baseline_tokens"]
        assert actual <= max_tokens, (
            f"Token budget exceeded: {actual} tokens used, limit is {max_tokens}. "
            f"Reduce the number of enabled tools/prompts/resources or increase max_tokens."
        )

    return report


def _print_report(report: TokenReport) -> None:
    """Print a simple token report table to stdout."""
    print(f"\n── Token Report (scenario={report.scenario!r}, tokenizer={report.tokenizer!r}) ──")
    print(f"{'Name':<40} {'Type':<10} {'Status':<10} {'Tokens':>8}")
    print("-" * 72)
    for item in report.items:
        print(f"{item.name:<40} {item.item_type:<10} {item.status:<10} {item.tokens:>8}")
    print("-" * 72)
    s = report.summary
    print(
        f"Tools: {s['tools_enabled']} enabled / {s['tools_disabled']} disabled  |  "
        f"Total tokens: {s['total_baseline_tokens']}"
    )


@pytest.fixture
def token_report():
    """Provide a callable that builds a TokenReport for a FastMCP app.

    Usage::

        async def test_something(token_report, sample_app):
            report = await token_report(sample_app)
            assert report.summary["total_baseline_tokens"] > 0
    """

    async def get_report(app: Any, **kwargs: Any) -> TokenReport:
        counter = TokenCounter(app)
        return await counter.build_report(**kwargs)

    return get_report

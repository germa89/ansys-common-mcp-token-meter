"""Token counting engine."""

from __future__ import annotations

import enum
import json
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from fastmcp import FastMCP


class TokenizerBackend(str, enum.Enum):
    """Supported tokenizer backends."""

    CL100K_BASE = "cl100k_base"
    O200K_BASE = "o200k_base"
    P50K_BASE = "p50k_base"
    CHARS = "chars"


def count_tokens(text: str, backend: TokenizerBackend = TokenizerBackend.CL100K_BASE) -> int:
    """Count tokens in *text* using *backend*.

    Falls back to CHARS (``len(text) // 4``) when tiktoken is unavailable.
    """
    if backend is TokenizerBackend.CHARS:
        return len(text) // 4

    try:
        import tiktoken  # noqa: PLC0415

        enc = tiktoken.get_encoding(backend.value)
        return len(enc.encode(text))
    except ImportError:
        warnings.warn(
            f"tiktoken is not installed; falling back to CHARS estimator for backend '{backend.value}'.",
            stacklevel=2,
        )
        return len(text) // 4


@dataclass
class TokenItemReport:
    """Per-item token report entry."""

    name: str
    item_type: Literal["tool", "prompt", "resource"]
    status: Literal["enabled", "disabled"]
    tags: list[str]
    tokens: int
    characters: int


@dataclass
class TokenReport:
    """Full token report for a scenario."""

    scenario: str
    tokenizer: str
    items: list[TokenItemReport] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class TokenCounter:
    """Counts tokens for a FastMCP application."""

    def __init__(
        self,
        app: FastMCP,
        tokenizer: TokenizerBackend = TokenizerBackend.CL100K_BASE,
        scenarios: dict | None = None,
    ) -> None:
        self._app = app
        self._tokenizer = tokenizer
        self._scenarios = scenarios or {}

    async def build_report(
        self,
        scenario: str = "default",
        disable_tags: set[str] | None = None,
        enable_tags: set[str] | None = None,
        filter_name: str | None = None,
        filter_type: str | None = None,
    ) -> TokenReport:
        """Build a token report for *scenario*.

        Parameters
        ----------
        scenario:
            Scenario name; looked up in ``self._scenarios`` then in the built-in
            ``DEFAULT_SCENARIOS``.
        disable_tags:
            Ad-hoc tags to disable on top of the scenario config.
        enable_tags:
            Ad-hoc tags to enable (re-enable) on top of the scenario config.
        filter_name:
            Only include the item with this name.
        filter_type:
            Only include items of this type (``"tool"``, ``"prompt"``, or ``"resource"``).
        """
        from ansys.common.mcp.token_meter.scenarios import DEFAULT_SCENARIOS  # noqa: PLC0415

        # Resolve scenario config
        all_scenarios = {**DEFAULT_SCENARIOS, **self._scenarios}
        if scenario not in all_scenarios:
            raise ValueError(f"Unknown scenario '{scenario}'. Available: {sorted(all_scenarios)}")
        scenario_cfg = all_scenarios[scenario]
        effective_disable = set(scenario_cfg.get("disable_tags", set()))
        if disable_tags:
            effective_disable |= set(disable_tags)
        effective_enable = set(enable_tags or set())

        items: list[TokenItemReport] = []

        # ── Tools ──────────────────────────────────────────────────────────────
        tools = await self._app.list_tools()
        for tool in tools:
            tool_tags: set[str] = set(getattr(tool, "tags", None) or set())
            disabled = bool((effective_disable & tool_tags) and not (effective_enable & tool_tags))
            status: Literal["enabled", "disabled"] = "disabled" if disabled else "enabled"

            # Serialize to MCP wire-format JSON via to_mcp_tool()
            mcp_tool = tool.to_mcp_tool()
            tool_json = json.dumps(mcp_tool.model_dump(), ensure_ascii=False)
            chars = len(tool_json)
            tokens = count_tokens(tool_json, self._tokenizer)

            items.append(
                TokenItemReport(
                    name=tool.name,
                    item_type="tool",
                    status=status,
                    tags=sorted(tool_tags),
                    tokens=tokens,
                    characters=chars,
                )
            )

        # ── Prompts ────────────────────────────────────────────────────────────
        prompts = await self._app.list_prompts()
        for prompt in prompts:
            mcp_prompt = prompt.to_mcp_prompt()
            prompt_json = json.dumps(mcp_prompt.model_dump(), ensure_ascii=False)
            chars = len(prompt_json)
            tokens = count_tokens(prompt_json, self._tokenizer)

            items.append(
                TokenItemReport(
                    name=prompt.name,
                    item_type="prompt",
                    status="enabled",
                    tags=[],
                    tokens=tokens,
                    characters=chars,
                )
            )

        # ── Resources ──────────────────────────────────────────────────────────
        resources = await self._app.list_resources()
        for resource in resources:
            mcp_resource = resource.to_mcp_resource()
            resource_json = json.dumps(mcp_resource.model_dump(), ensure_ascii=False)
            chars = len(resource_json)
            tokens = count_tokens(resource_json, self._tokenizer)

            items.append(
                TokenItemReport(
                    name=str(resource.uri),
                    item_type="resource",
                    status="enabled",
                    tags=[],
                    tokens=tokens,
                    characters=chars,
                )
            )

        # ── Apply filters ──────────────────────────────────────────────────────
        if filter_name is not None:
            items = [i for i in items if i.name == filter_name]
        if filter_type is not None:
            items = [i for i in items if i.item_type == filter_type]

        # ── Summary ────────────────────────────────────────────────────────────
        tool_items = [i for i in items if i.item_type == "tool"]
        prompt_items = [i for i in items if i.item_type == "prompt"]
        resource_items = [i for i in items if i.item_type == "resource"]

        tools_enabled = sum(1 for t in tool_items if t.status == "enabled")
        tools_disabled = sum(1 for t in tool_items if t.status == "disabled")
        tool_tokens = sum(t.tokens for t in tool_items if t.status == "enabled")
        prompt_tokens = sum(p.tokens for p in prompt_items)
        resource_tokens = sum(r.tokens for r in resource_items)

        summary = {
            "tools_enabled": tools_enabled,
            "tools_disabled": tools_disabled,
            "tools_total": len(tool_items),
            "tool_tokens": tool_tokens,
            "prompt_tokens": prompt_tokens,
            "resource_tokens": resource_tokens,
            "total_baseline_tokens": tool_tokens + prompt_tokens + resource_tokens,
        }

        return TokenReport(
            scenario=scenario,
            tokenizer=self._tokenizer.value,
            items=items,
            summary=summary,
        )

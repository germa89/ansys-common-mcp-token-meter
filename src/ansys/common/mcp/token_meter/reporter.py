"""Report formatters."""

from __future__ import annotations

import json

from ansys.common.mcp.token_meter.engine import TokenReport


def format_json(report: TokenReport) -> str:
    """Serialize *report* to JSON (indent=2)."""
    tools = [i for i in report.items if i.item_type == "tool"]
    prompts = [i for i in report.items if i.item_type == "prompt"]
    resources = [i for i in report.items if i.item_type == "resource"]

    data = {
        "scenario": report.scenario,
        "tokenizer": report.tokenizer,
        "summary": report.summary,
        "tools": [
            {
                "name": t.name,
                "status": t.status,
                "tags": t.tags,
                "tokens": t.tokens,
                "characters": t.characters,
            }
            for t in tools
        ],
        "prompts": [
            {
                "name": p.name,
                "tokens": p.tokens,
                "characters": p.characters,
            }
            for p in prompts
        ],
        "resources": [
            {
                "name": r.name,
                "tokens": r.tokens,
                "characters": r.characters,
            }
            for r in resources
        ],
    }
    return json.dumps(data, indent=2)


def format_table(report: TokenReport, title: str = "MCP Token Report") -> str:  # noqa: PLR0912
    """Render *report* as a human-readable table."""
    lines: list[str] = []
    sep = "─" * 72

    lines.append(title)
    lines.append(f"Scenario: {report.scenario} | Tokenizer: {report.tokenizer}")
    lines.append(sep)

    tools = [i for i in report.items if i.item_type == "tool"]
    prompts = [i for i in report.items if i.item_type == "prompt"]
    resources = [i for i in report.items if i.item_type == "resource"]

    s = report.summary

    # ── TOOLS ──────────────────────────────────────────────────────────────
    if tools:
        te, td, tt = s.get("tools_enabled", 0), s.get("tools_disabled", 0), s.get("tools_total", 0)
        lines.append(f"\nTOOLS  ({te} enabled / {td} disabled / {tt} total)\n")
        col_name = 38
        col_status = 10
        col_tags = 22
        hdr = f"  {'Name':<{col_name}}{'Status':<{col_status}}{'Tags':<{col_tags}}{'Tokens':>7}"
        lines.append(hdr)
        lines.append("  " + "─" * 69)
        for t in sorted(tools, key=lambda x: x.name):
            tags_str = ",".join(t.tags) if t.tags else ""
            status_str = t.status.upper()
            lines.append(f"  {t.name:<{col_name}}{status_str:<{col_status}}{tags_str:<{col_tags}}{t.tokens:>7}")

    # ── PROMPTS ────────────────────────────────────────────────────────────
    if prompts:
        lines.append(f"\nPROMPTS  ({len(prompts)} total)\n")
        for p in sorted(prompts, key=lambda x: x.name):
            lines.append(f"  {p.name:<70}{p.tokens:>7}")

    # ── RESOURCES ──────────────────────────────────────────────────────────
    if resources:
        lines.append(f"\nRESOURCES  ({len(resources)} total)\n")
        for r in sorted(resources, key=lambda x: x.name):
            lines.append(f"  {r.name:<70}{r.tokens:>7}")

    # ── SUMMARY ────────────────────────────────────────────────────────────
    lines.append("\nSUMMARY")
    lines.append(f"  {'Tool tokens (enabled):':<38}{s.get('tool_tokens', 0):>9,}")
    lines.append(f"  {'Prompt tokens:':<38}{s.get('prompt_tokens', 0):>9,}")
    lines.append(f"  {'Resource tokens:':<38}{s.get('resource_tokens', 0):>9,}")
    lines.append("  " + "─" * 40)
    lines.append(f"  {'Total baseline:':<38}{s.get('total_baseline_tokens', 0):>9,} tokens")

    return "\n".join(lines)

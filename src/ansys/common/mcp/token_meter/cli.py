"""CLI entry point for mcp-token-meter."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import sys


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-token-meter",
        description="Count tokens in a FastMCP application.",
    )
    parser.add_argument(
        "--app",
        required=True,
        help="Dotted path to FastMCP app object, e.g. 'mymodule:app' or 'mymodule.sub:app'.",
    )
    parser.add_argument(
        "--format",
        dest="format",
        default="table",
        choices=["table", "json"],
        help="Output format (default: table).",
    )
    parser.add_argument(
        "--tokenizer",
        default="cl100k_base",
        choices=["cl100k_base", "o200k_base", "p50k_base", "chars"],
        help="Tokenizer backend (default: cl100k_base).",
    )
    parser.add_argument(
        "--scenario",
        default="default",
        help="Scenario name to use (default: default).",
    )
    parser.add_argument(
        "--scenario-file",
        default=None,
        metavar="PATH",
        help="Path to a TOML or JSON scenario file.",
    )
    parser.add_argument(
        "--disable-tags",
        default=None,
        metavar="TAGS",
        help="Comma-separated tags to disable.",
    )
    parser.add_argument(
        "--enable-tags",
        default=None,
        metavar="TAGS",
        help="Comma-separated tags to enable (re-enable).",
    )
    parser.add_argument(
        "--tool",
        default=None,
        metavar="NAME",
        help="Filter output to a single tool by name.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        metavar="NAME",
        help="Filter output to a single prompt by name.",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    return parser.parse_args(argv)


def _load_app(app_path: str):
    """Import and return the FastMCP app object from a dotted path.

    Accepts both ``module:attr`` and ``module.attr`` notation.
    """
    if ":" in app_path:
        module_path, attr = app_path.rsplit(":", 1)
    else:
        module_path, attr = app_path.rsplit(".", 1)

    module = importlib.import_module(module_path)
    return getattr(module, attr)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, 1 on error."""
    args = _parse_args(argv)

    # Load app
    try:
        app = _load_app(args.app)
    except (ImportError, ModuleNotFoundError) as exc:
        print(f"Error: cannot import app '{args.app}': {exc}", file=sys.stderr)
        return 1
    except AttributeError as exc:
        print(f"Error: attribute not found in '{args.app}': {exc}", file=sys.stderr)
        return 1

    # Load scenarios
    try:
        from ansys.common.mcp.token_meter.scenarios import load_scenarios  # noqa: PLC0415

        scenarios = load_scenarios(scenario_file=args.scenario_file)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Resolve tokenizer
    from ansys.common.mcp.token_meter.engine import TokenCounter, TokenizerBackend  # noqa: PLC0415

    tokenizer = TokenizerBackend(args.tokenizer)

    # Parse tag filters
    disable_tags = set(args.disable_tags.split(",")) if args.disable_tags else None
    enable_tags = set(args.enable_tags.split(",")) if args.enable_tags else None

    # Determine filter_type
    filter_name: str | None = None
    filter_type: str | None = None
    if args.tool:
        filter_name = args.tool
        filter_type = "tool"
    elif args.prompt:
        filter_name = args.prompt
        filter_type = "prompt"

    # Build report
    counter = TokenCounter(app, tokenizer, scenarios)
    try:
        report = asyncio.run(
            counter.build_report(
                scenario=args.scenario,
                disable_tags=disable_tags,
                enable_tags=enable_tags,
                filter_name=filter_name,
                filter_type=filter_type,
            )
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Format output
    from ansys.common.mcp.token_meter.reporter import format_json, format_table  # noqa: PLC0415

    if args.format == "json":
        output = format_json(report)
    else:
        output = format_table(report)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output)
                fh.write("\n")
        except OSError as exc:
            print(f"Error: cannot write to '{args.output}': {exc}", file=sys.stderr)
            return 1
    else:
        print(output)

    return 0

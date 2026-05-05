"""Tests for the CLI entry point."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from ansys.common.mcp.token_meter.cli import main

APP_PATH = "tests.fixtures.sample_app:app"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_main(*args: str) -> tuple[int, str, str]:
    """Run main() with *args and return (returncode, stdout, stderr)."""
    rc = main(list(args))
    return rc


# ---------------------------------------------------------------------------
# Basic invocation
# ---------------------------------------------------------------------------


def test_basic_table(capsys):
    """Default invocation produces a table with expected sections."""
    rc = main(["--app", APP_PATH])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TOOLS" in out
    assert "PROMPTS" in out
    assert "SUMMARY" in out
    assert "add" in out
    assert "multiply" in out
    assert "greet" in out
    assert "system_prompt" in out


def test_json_format(capsys):
    """--format json produces valid JSON with expected keys."""
    rc = main(["--app", APP_PATH, "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "tools" in data
    assert "summary" in data
    assert "scenario" in data
    tool_names = {t["name"] for t in data["tools"]}
    assert "add" in tool_names
    assert "multiply" in tool_names
    assert "greet" in tool_names


def test_tokenizer_chars(capsys):
    """--tokenizer chars runs without error."""
    rc = main(["--app", APP_PATH, "--tokenizer", "chars"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SUMMARY" in out


def test_scenario_default(capsys):
    """--scenario default is the baseline: all tools enabled."""
    rc = main(["--app", APP_PATH, "--scenario", "default"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "TOOLS" in out


# ---------------------------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------------------------


def test_disable_tags_optional(capsys):
    """--disable-tags optional disables multiply and greet."""
    rc = main(["--app", APP_PATH, "--disable-tags", "optional"])
    assert rc == 0
    out = capsys.readouterr().out
    # multiply and greet carry the 'optional' tag → disabled
    assert "DISABLED" in out.upper() or "disabled" in out
    # add is still enabled (math + core only)
    assert "add" in out


def test_enable_and_disable_tags(capsys):
    """--enable-tags math with --disable-tags optional keeps add enabled."""
    rc = main(["--app", APP_PATH, "--disable-tags", "optional", "--enable-tags", "math"])
    assert rc == 0
    out = capsys.readouterr().out
    # multiply has both 'math' and 'optional' — enable-tags re-enables it
    assert "multiply" in out
    assert "add" in out


# ---------------------------------------------------------------------------
# Name filters
# ---------------------------------------------------------------------------


def test_filter_tool(capsys):
    """--tool add returns only the 'add' tool."""
    rc = main(["--app", APP_PATH, "--tool", "add"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "add" in out
    assert "multiply" not in out
    assert "greet" not in out


def test_filter_prompt(capsys):
    """--prompt system_prompt returns only that prompt."""
    rc = main(["--app", APP_PATH, "--prompt", "system_prompt"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "system_prompt" in out
    assert "add" not in out


# ---------------------------------------------------------------------------
# Output file
# ---------------------------------------------------------------------------


def test_output_file(tmp_path, capsys):
    """--output writes to file; nothing on stdout."""
    out_file = tmp_path / "report.txt"
    rc = main(["--app", APP_PATH, "--output", str(out_file)])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert stdout == ""
    content = out_file.read_text(encoding="utf-8")
    assert "SUMMARY" in content


def test_output_file_json(tmp_path):
    """--output with --format json writes valid JSON file."""
    out_file = tmp_path / "report.json"
    rc = main(["--app", APP_PATH, "--format", "json", "--output", str(out_file)])
    assert rc == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "tools" in data


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_invalid_app_returns_1(capsys):
    """An unknown --app path returns exit code 1."""
    rc = main(["--app", "nonexistent.module:app"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Error" in err


def test_missing_app_exits_2():
    """Running without --app causes argparse to raise SystemExit(2)."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2


def test_invalid_scenario_returns_1(capsys):
    """An unknown --scenario returns exit code 1."""
    rc = main(["--app", APP_PATH, "--scenario", "nonexistent_scenario"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Error" in err


def test_invalid_scenario_file_returns_1(capsys):
    """A missing --scenario-file returns exit code 1."""
    rc = main(["--app", APP_PATH, "--scenario-file", "/nonexistent/path/scenarios.toml"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Error" in err


# ---------------------------------------------------------------------------
# Subprocess / -m invocation
# ---------------------------------------------------------------------------


def test_module_invocation_subprocess():
    """python -m ansys.common.mcp.token_meter --app ... exits 0 and has output."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ansys.common.mcp.token_meter",
            "--app",
            APP_PATH,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "SUMMARY" in result.stdout

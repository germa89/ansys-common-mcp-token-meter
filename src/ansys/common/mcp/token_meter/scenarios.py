"""Scenario management."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SCENARIOS: dict[str, dict] = {
    "default": {
        "disable_tags": set(),
        "description": "All tools as registered",
    }
}


def load_scenarios(
    config: dict | None = None,
    scenario_file: str | None = None,
) -> dict[str, dict]:
    """Load and merge user-defined scenarios.

    Parameters
    ----------
    config:
        In-memory scenario dict (e.g. from ``pyproject.toml`` ``[tool.mcp-token-meter.scenarios]``).
    scenario_file:
        Path to a JSON or TOML file containing scenario definitions.

    Returns
    -------
    dict
        Merged scenarios (user scenarios override ``DEFAULT_SCENARIOS`` keys except ``"default"``).
    """
    user_scenarios: dict[str, dict] = {}

    if scenario_file is not None:
        path = Path(scenario_file)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_file}")
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            user_scenarios = json.loads(text)
        elif path.suffix in {".toml", ".tml"}:
            try:
                import tomllib  # Python 3.11+  # noqa: PLC0415
            except ImportError:
                import tomli as tomllib  # noqa: PLC0415
            user_scenarios = tomllib.loads(text)
        else:
            raise ValueError(f"Unsupported scenario file format: {path.suffix!r} (use .json or .toml)")

    if config is not None:
        user_scenarios.update(config)

    # Normalize disable_tags to sets
    merged: dict[str, dict] = {**DEFAULT_SCENARIOS}
    for name, cfg in user_scenarios.items():
        normalized = dict(cfg)
        if "disable_tags" in normalized:
            normalized["disable_tags"] = set(normalized["disable_tags"])
        merged[name] = normalized

    return merged

"""Allow running as python -m ansys.common.mcp.token_meter."""
from ansys.common.mcp.token_meter.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

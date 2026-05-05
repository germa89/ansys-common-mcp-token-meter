"""Shared test fixtures."""

import pytest
from fastmcp import FastMCP


@pytest.fixture
def sample_app():
    """Minimal FastMCP application for testing."""
    app = FastMCP(name="test-app", instructions="A test MCP server")

    @app.tool(tags={"core"})
    def add(x: int, y: int) -> int:
        """Add two numbers."""
        return x + y

    @app.tool(tags={"core"})
    def subtract(x: int, y: int) -> int:
        """Subtract y from x."""
        return x - y

    @app.tool(tags={"optional"})
    def multiply(x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    @app.prompt()
    def system_prompt() -> str:
        """Return the system prompt."""
        return "You are a helpful calculator assistant."

    return app

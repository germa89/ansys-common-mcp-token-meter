"""Standalone FastMCP app for CLI and integration testing."""
from fastmcp import FastMCP

app = FastMCP(name="sample-app", instructions="Sample MCP server for testing")


@app.tool(tags={"math", "core"})
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


@app.tool(tags={"math", "optional"})
def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y


@app.tool(tags={"string", "optional"})
def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}!"


@app.prompt()
def system_prompt() -> str:
    """Return the system prompt."""
    return "You are a helpful assistant."

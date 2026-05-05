# ansys-common-mcp-token-meter

Token counting and budget enforcement for [FastMCP](https://github.com/jlowin/fastmcp)-based MCP servers.

## Overview

`ansys-common-mcp-token-meter` introspects a FastMCP application to enumerate tools, prompts, and resources, serializes them as MCP wire-format JSON, and counts tokens via a pluggable tokenizer backend.

## Features

- **Token counting**: Count tokens for tools, prompts, and resources using tiktoken or character-estimate fallback
- **Scenarios**: Define tool enable/disable profiles based on tag sets
- **CLI**: Standalone usage and CI integration
- **Pytest plugin**: `@token_budget` decorator for budget assertions in tests

## Installation

```bash
pip install ansys-common-mcp-token-meter
# With tiktoken support:
pip install "ansys-common-mcp-token-meter[tiktoken]"
```

## Quick Start

```python
from fastmcp import FastMCP
from ansys.common.mcp.token_meter import TokenCounter, TokenizerBackend

app = FastMCP(name="my-server")

@app.tool()
def my_tool(x: int) -> int:
    """My tool."""
    return x

import asyncio
counter = TokenCounter(app, tokenizer=TokenizerBackend.CL100K_BASE)
report = asyncio.run(counter.build_report())
print(f"Total tokens: {report.summary['total_baseline_tokens']}")
```

## CLI

```bash
mcp-token-meter --app mymodule:app --format table
```

## License

MIT

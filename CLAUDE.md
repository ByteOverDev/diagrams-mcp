# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

MCP server that exposes mingrammer/diagrams (cloud architecture diagram library) as tools over the Model Context Protocol. Built on FastMCP. Requires Graphviz installed on the system.

## Commands

```bash
# Run tests
pytest
pytest tests/test_discovery.py           # single file
pytest tests/test_discovery.py::test_list_nodes  # single test

# Lint and format
ruff check .
ruff format .

# Run the MCP server
diagrams-mcp-server
```

## Architecture

The server (`server.py`) creates a root `FastMCP("diagrams")` instance and mounts sub-applications for each tool group:

```
server.py          → mcp = FastMCP("diagrams")
  ├── tools/discovery.py  → discovery = FastMCP("Discovery")  [mounted]
  ├── tools/render.py     → render = FastMCP("Render")        [mounted]
  └── sandbox.py          → sandboxed subprocess execution
```

**Tool registration pattern**: Each tool module creates its own `FastMCP` instance, decorates functions with `@instance.tool`, and the root server mounts them via `mcp.mount()`.

**Discovery tools** use `pkgutil.iter_modules` + `importlib.import_module` to dynamically introspect the `diagrams` package at runtime — no hardcoded node lists.

**render_diagram** executes user-provided diagrams code in a sandboxed subprocess (`sandbox.py`) with a minimal env (only PATH, HOME, TMPDIR), monkey-patches `Diagram.__init__` to force `show=False` and redirect output to a temp directory, then returns the resulting PNG as `fastmcp.utilities.types.Image`. Timeout is 25s at the subprocess level, 30s at the tool level.

## MCP Tools

**Discovery (3 tools):**
- `list_providers()` → `list[str]` — Returns provider names (`aws`, `gcp`, `k8s`, `azure`, `onprem`, etc.)
- `list_services(provider)` → `list[str]` — Returns service categories within a provider (e.g. `aws` → `compute`, `database`, `network`)
- `list_nodes(provider, service)` → `list[str]` — Returns node class names for a provider.service pair (e.g. `aws.compute` → `EC2`, `Lambda`, `Fargate`)

**Render (1 tool):**
- `render_diagram(code, filename="diagram")` → `Image` (PNG) — Executes a complete Python script using the diagrams library in a sandboxed subprocess. The code must use `from diagrams import ...` and a `with Diagram(...):` block. The sandbox forces `show=False` and captures the output PNG.

## Key Dependencies

- `fastmcp>=3.0` — MCP server framework. Tools use `@app.tool` decorator, errors use `fastmcp.exceptions.ToolError`
- `diagrams>=0.23` — The underlying diagram library being exposed. Providers live at `diagrams.<provider>.<service>.<Node>`

## Ruff Config

Target Python 3.11, line length 100, rules: E, F, I, N, W, UP.

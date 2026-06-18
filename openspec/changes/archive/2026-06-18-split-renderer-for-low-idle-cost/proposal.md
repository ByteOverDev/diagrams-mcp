## Why

The production Railway deployment now holds a stable idle memory baseline around 690 MB because the always-on MCP server includes every heavy rendering dependency: Python diagrams, Graphviz, Node/Mermaid CLI, Chromium, Java, and PlantUML. The goal is to lower idle cost by keeping the interactive MCP surface lightweight and moving expensive rendering work out of the always-on process.

## What Changes

- Split the current all-in-one deployment into a lightweight MCP facade and a separate render execution path.
- Keep discovery, references, prompts, equivalence lookup, and request routing in the low-memory always-on service.
- Move Graphviz, Mermaid/Chromium, and PlantUML/Java execution behind an on-demand renderer boundary.
- Move rendered image delivery away from process-local memory where practical, using external object storage or an equivalent durable temporary output mechanism.
- Preserve existing MCP tool behavior for clients unless a specific compatibility issue is discovered during design.
- Add operational observability for idle memory, render memory, render duration, failures, and output storage lifecycle.

## Capabilities

### New Capabilities
- `low-idle-mcp-facade`: Defines the lightweight always-on MCP service responsibilities and client-facing behavior.
- `on-demand-renderer`: Defines the separated rendering execution capability for diagrams, Mermaid, and PlantUML.
- `external-image-delivery`: Defines temporary rendered image storage and download delivery outside process-local memory.
- `render-observability`: Defines metrics/logging needed to verify lower idle cost and diagnose render resource usage.

### Modified Capabilities

None. No existing specs are present.

## Impact

- Affected code areas: `src/diagrams_mcp/server.py`, `src/diagrams_mcp/tools/render.py`, `src/diagrams_mcp/tools/mermaid.py`, `src/diagrams_mcp/tools/plantuml.py`, `src/diagrams_mcp/sandbox.py`, and `src/diagrams_mcp/image_store.py`.
- Affected deployment files: `Dockerfile`, `railway.toml`, and any new deployment/configuration files for the facade, renderer, and image storage.
- Affected infrastructure: Railway service topology and likely Cloudflare/R2 or equivalent object storage if selected during implementation.
- Client API impact should be minimized: existing render tools should continue returning inline images or temporary download URLs according to existing semantics.

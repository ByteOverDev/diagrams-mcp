# low-idle-mcp-facade Specification

## Purpose
Define the always-on MCP facade behavior and idle footprint expectations after renderer dependencies move behind a boundary.

## Requirements

### Requirement: Facade excludes renderer-only runtime dependencies
The always-on MCP facade SHALL run without requiring Graphviz, Chromium, Mermaid CLI, Java, or PlantUML to be installed in its runtime image.

#### Scenario: Facade starts without render engines
- **WHEN** the facade service starts in an environment that lacks renderer-only binaries
- **THEN** discovery, references, prompts, equivalence, health, and MCP protocol handling remain available

#### Scenario: Facade does not import render-only modules at startup
- **WHEN** the facade process starts
- **THEN** it MUST avoid importing modules that require renderer-only native binaries unless handling a render request through the renderer boundary

### Requirement: Facade preserves client-facing MCP tool availability
The facade SHALL expose the existing MCP tools needed by clients, including render tools, while delegating render execution across the renderer boundary.

#### Scenario: Client lists tools
- **WHEN** a client connects to the MCP service and lists available tools
- **THEN** the existing discovery and render tools are present unless explicitly deprecated by a later change

#### Scenario: Client invokes render tool through facade
- **WHEN** a client invokes a render tool on the facade
- **THEN** the facade validates and routes the request to the configured renderer implementation

### Requirement: Facade has a measurable idle footprint target
The facade SHALL define and report an idle memory target after renderer-only dependencies are removed.

#### Scenario: Idle memory is measured after deployment
- **WHEN** the split facade has been deployed and receives no render requests for a representative idle window
- **THEN** operators can compare measured idle memory against the configured target and the pre-split baseline

# on-demand-renderer Specification

## Purpose
Define renderer service behavior for executing diagram workloads outside the MCP facade.

## Requirements

### Requirement: Renderer executes all supported render engines
The renderer SHALL support the existing diagram rendering engines: Python diagrams with Graphviz, Mermaid via Mermaid CLI/Chromium, and PlantUML via Java/PlantUML.

#### Scenario: Diagrams render request
- **WHEN** the facade submits a valid diagrams render request
- **THEN** the renderer returns a rendered artifact or a structured render error

#### Scenario: Mermaid render request
- **WHEN** the facade submits a valid Mermaid render request
- **THEN** the renderer returns a rendered artifact or a structured render error

#### Scenario: PlantUML render request
- **WHEN** the facade submits a valid PlantUML render request
- **THEN** the renderer returns a rendered artifact or a structured render error

### Requirement: Renderer isolates render execution from the facade
The renderer SHALL execute render workloads outside the facade process so renderer memory growth, crashes, and subprocess behavior do not directly increase facade RSS.

#### Scenario: Renderer memory spike
- **WHEN** a render operation causes a renderer memory spike
- **THEN** the facade process remains alive and its memory usage is not directly increased by renderer subprocess RSS

#### Scenario: Renderer failure
- **WHEN** the renderer fails a render operation
- **THEN** the facade receives a structured failure and returns a client-safe tool error

### Requirement: Renderer enforces resource limits
The renderer SHALL enforce timeout, memory, filesystem, and network restrictions equivalent to or stricter than the current sandbox behavior.

#### Scenario: Render exceeds timeout
- **WHEN** a render operation exceeds the configured timeout
- **THEN** the renderer terminates the render workload and returns a timeout error

#### Scenario: Render attempts disallowed network access
- **WHEN** diagram code attempts disallowed network access
- **THEN** the renderer blocks the access and fails safely

### Requirement: Renderer supports independent scaling or lifecycle control
The renderer SHALL be deployable with lifecycle behavior independent from the facade, including the ability to run only when render capacity is needed if the selected platform supports it.

#### Scenario: Facade remains available while renderer is unavailable
- **WHEN** the renderer is unavailable
- **THEN** non-render MCP tools remain available through the facade

#### Scenario: Renderer capacity changes
- **WHEN** render demand changes
- **THEN** renderer capacity or lifecycle settings can be adjusted without redeploying the facade code

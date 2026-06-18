## 1. Baseline And Import Audit

- [x] 1.1 Record current Railway idle memory, memory limit, render traffic pattern, and post-render memory behavior as the pre-split baseline.
- [x] 1.2 Audit startup imports to identify renderer-only modules imported by the always-on server path.
- [x] 1.3 Add or update tests that prove discovery, references, prompts, equivalence, and health can work without invoking render engines.
- [x] 1.4 Define the target facade idle memory threshold for release validation.

## 2. Output Delivery Boundary

- [x] 2.1 Introduce an output storage interface that can return inline image data or temporary download URLs.
- [x] 2.2 Keep the current in-memory image store as the local implementation behind the new interface.
- [x] 2.3 Add an external temporary storage implementation or adapter for the selected object store.
- [x] 2.4 Preserve existing PNG, SVG, and PDF delivery behavior through the new storage interface.
- [x] 2.5 Add tests for valid URL delivery, expired outputs, oversized outputs, and content type handling.

## 3. Renderer Boundary

- [x] 3.1 Define a renderer request/response contract covering diagrams, Mermaid, PlantUML, output format, filename, success artifacts, and structured errors.
- [x] 3.2 Add a renderer client/interface used by the MCP render tools.
- [x] 3.3 Implement an in-process renderer adapter using the existing `run_code` and `run_cli` paths for migration compatibility.
- [x] 3.4 Route existing render tools through the renderer interface without changing client-facing tool names.
- [x] 3.5 Add tests that render tools handle renderer success, renderer failure, timeout errors, and malformed output through the interface.

## 4. Separate Renderer Service

- [x] 4.1 Create a renderer service entry point that exposes the renderer contract over the selected transport.
- [x] 4.2 Move or package Graphviz, Mermaid CLI, Chromium, Java, PlantUML, and sandbox execution into the renderer service image.
- [x] 4.3 Enforce renderer timeouts and sandbox/resource restrictions equivalent to or stricter than the current behavior.
- [x] 4.4 Add renderer service tests for diagrams, Mermaid, PlantUML, timeout, and structured error responses.
- [x] 4.5 Add configuration for the facade to select in-process rendering or remote renderer mode.

## 5. Facade Slimming

- [x] 5.1 Create a slim facade runtime image that excludes Graphviz, Node/Mermaid CLI, Chromium, Java, and PlantUML.
- [x] 5.2 Ensure the slim facade starts and serves non-render MCP capabilities without renderer-only binaries installed.
- [x] 5.3 Ensure render requests in remote mode delegate to the renderer service and do not import renderer-only dependencies in the facade process.
- [x] 5.4 Add deployment configuration for separate facade and renderer services.

## 6. Observability And Operations

- [x] 6.1 Add structured logs for render dispatch, completion, failure category, duration, renderer type, output format, and delivery mode.
- [x] 6.2 Add metrics or log fields that distinguish facade idle memory from renderer execution memory.
- [x] 6.3 Add operational documentation for reading Railway or platform metrics before and after the split.
- [x] 6.4 Add rollback instructions for returning the facade to in-process renderer mode if the remote renderer fails.

## 7. Validation And Rollout

- [x] 7.1 Run the full test suite and lint/format checks.
- [x] 7.2 Deploy the split architecture to a non-production or preview environment if available.
- [x] 7.3 Validate discovery and reference tools with the renderer unavailable.
- [x] 7.4 Validate each render engine through the facade using remote renderer mode.
- [x] 7.5 Compare post-split facade idle memory against the pre-split 0.69 GB baseline and the target threshold.
- [x] 7.6 Promote to production only after client-facing render behavior and output delivery compatibility are verified.

Production validation notes, 2026-06-18:
- Split production facade: `https://diagrams-mcp-facade-production-8fff.up.railway.app`.
- Verified MCP tool listing includes `list_providers`, `render_diagram`, `render_mermaid`, and `render_plantuml`.
- Verified `render_diagram`, `render_mermaid`, and `render_plantuml` through the facade using the remote renderer.
- Verified returned `/images/{token}` links respond `200` with `image/png` content.
- Verified discovery still works with `DIAGRAMS_RENDERER_URL` pointed at an unavailable endpoint.
- Current memory: old `diagrams-mcp` ~0.69 GB; split facade ~0.067 GB current / ~0.133 GB peak; renderer ~0.064 GB current / ~0.184 GB peak.

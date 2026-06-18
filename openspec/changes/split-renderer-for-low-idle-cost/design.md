## Context

The current deployment runs as a single always-on Railway Dockerfile service. That service hosts the FastMCP HTTP server and also carries every renderer dependency: Python diagrams, Graphviz, Node/Mermaid CLI, Chromium/Puppeteer, Java, and PlantUML. Railway metrics show the post-session-fix deployment is stable, but its current idle memory baseline is about 0.69 GB with an 8 GB limit.

The previous multi-GB memory climb was addressed by running FastMCP with `stateless_http=True`. The remaining problem is idle cost: a renderer-capable container remains resident even when clients are only discovering tools, reading references, or doing nothing.

Current request shape:

```text
Client
  │
  ▼
Always-on Railway service
  ├─ lightweight MCP operations
  ├─ render_diagram  -> Python subprocess + Graphviz
  ├─ render_mermaid  -> mmdc + Chromium
  ├─ render_plantuml -> Java + PlantUML
  └─ /images/{token} -> process-local image_store
```

Lower idle cost requires moving expensive render machinery out of the always-on path while preserving the MCP tool surface.

## Goals / Non-Goals

**Goals:**

- Reduce the memory footprint of the always-on MCP service by removing renderer-only runtime dependencies from it.
- Preserve existing MCP render tool behavior for clients where practical.
- Execute render jobs in an isolated on-demand renderer boundary that can scale independently from the MCP facade.
- Store temporary rendered outputs outside the facade process so download links do not require process-local image bytes.
- Add enough observability to prove idle memory improvements and diagnose render resource usage.

**Non-Goals:**

- Rewriting Graphviz, Mermaid, PlantUML, or diagrams rendering engines.
- Replacing existing diagram syntax or changing client-facing tool names as a first step.
- Implementing a fully Cloudflare-only renderer; Cloudflare Workers are a good facade candidate but are not a good host for native subprocess rendering.
- Guaranteeing zero idle cost for all infrastructure; the goal is materially lower always-on cost and bounded render cost.

## Decisions

### Decision: Split the system at the renderer boundary

The always-on MCP facade will own protocol handling, discovery, references, prompts, equivalence lookup, validation, and request orchestration. A separate renderer component will own all execution that requires Graphviz, Chromium, Java, or sandboxed Python subprocesses.

Rationale: discovery and references are cheap and should not require a heavy native runtime. Render requests are comparatively rare and bursty, so they are the right place to pay startup and memory cost.

Alternatives considered:

- Keep the all-in-one service and tune memory. This is lowest effort but cannot remove the baseline cost of the heavy runtime.
- Fully rewrite rendering on Cloudflare Workers. This conflicts with the native subprocess model used by Graphviz, Chromium, Java, and Python sandboxing.

### Decision: Preserve the MCP tool API initially

The facade should continue exposing the existing render tools. Internally, those tools may call the renderer component and return either inline image data or a temporary download URL according to the existing semantics.

Rationale: compatibility lets the infrastructure change ship without requiring client migration.

Alternatives considered:

- Introduce async-only render APIs immediately. This may be necessary later for long renders, but it is a larger client-facing change and should not be the first migration unless synchronous render timeouts force it.

### Decision: Use external temporary output storage for download links

Rendered outputs should be written to object storage or an equivalent external temporary store. The facade should not keep output bytes in a long-lived in-memory store for URL delivery.

Rationale: the current `ImageStore` intentionally allows up to 200 MB of process-local image data. External storage reduces facade RSS and makes output delivery independent from a specific process instance.

Alternatives considered:

- Keep `ImageStore` in the facade. This is simple but works against the lower idle memory goal.
- Return only inline images. This breaks SVG/PDF and large PNG behavior and does not fit existing output semantics.

### Decision: Treat Cloudflare as a facade/storage candidate, not the renderer

Cloudflare Workers and R2 are good candidates for the public facade and output delivery layer. The renderer should remain on infrastructure that supports native packages and subprocesses, such as Railway, Fly, Modal, or another container/job runtime.

Rationale: Workers are optimized for stateless request handling with CPU/memory limits. The existing renderer stack needs native binaries and controlled subprocess execution.

Alternatives considered:

- Use only Railway with two services. This still lowers facade memory if the facade service is slim, but does not benefit from Cloudflare's edge routing and R2 integration.

### Decision: Implement in migration phases

The change should be deployable incrementally:

```text
Phase 1: Instrument current service and establish baseline
Phase 2: Introduce external image delivery behind existing tools
Phase 3: Extract renderer interface behind current in-process calls
Phase 4: Deploy separate renderer and remove heavy deps from facade
Phase 5: Optional Cloudflare facade/R2 consolidation
```

Rationale: each phase should have an observable memory/cost effect and a rollback path.

## Risks / Trade-offs

- Renderer cold starts may increase first-render latency -> Mitigate with clear timeout handling, optional warm pool, and metrics for queue/render duration.
- Cross-service calls add failure modes -> Mitigate with structured errors, retries only where safe, and fallbacks during migration.
- External image storage adds lifecycle/security concerns -> Mitigate with short TTLs, unguessable object keys, explicit content types, and deletion/expiry policies.
- Synchronous MCP tool calls may not fit slow on-demand renders -> Mitigate by preserving synchronous behavior first and designing an async render path only if measured render durations require it.
- Splitting services increases deployment complexity -> Mitigate with small boundaries, config-driven renderer endpoint selection, and staged rollout.
- Removing heavy deps from the facade may accidentally break discovery behavior if imports are coupled -> Mitigate by auditing import boundaries and ensuring cheap modules do not import render-only dependencies at startup.

## Migration Plan

1. Establish baseline metrics for current Railway service: idle memory, render memory peak, render duration by engine, and image store occupancy if available.
2. Add an abstraction for rendered output delivery so tools can store outputs externally while preserving return semantics.
3. Add a renderer client/interface inside the facade while initially keeping the existing in-process renderer as the implementation.
4. Create a separate renderer service/container with the existing heavy dependencies and sandbox execution logic.
5. Route facade render tools to the renderer service in production behind configuration.
6. Remove Graphviz, Node/Mermaid CLI, Chromium, Java, and PlantUML from the facade image once remote rendering is active.
7. Compare Railway idle memory before and after the split; keep rollback available by restoring in-process renderer configuration.

## Open Questions

- Which platform should host the on-demand renderer: Railway service, Railway job pattern, Fly Machines, Modal, or another container runtime?
- Should the first external image store be Cloudflare R2, Railway volume-backed storage, or another object store?
- Does the MCP client ecosystem require render tools to remain strictly synchronous, or can large renders become async in a later change?
- What target idle memory should define success: under 200 MB, under 150 MB, or another cost-based threshold?

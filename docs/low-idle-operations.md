# Low Idle Cost Operations

## Pre-Split Baseline

Railway production metrics captured during discovery for `diagrams-mcp`:

| Metric | Value |
| --- | --- |
| Service | `diagrams-mcp` |
| Environment | `production` |
| Memory limit | `8 GB` |
| Current idle memory | `~0.689 GB` |
| 24h peak memory | `~0.691 GB` |
| OOM or restart events in last 24h | none |

The prior multi-GB memory climb was addressed by `stateless_http=True`. The
remaining cost issue is the stable always-on baseline caused by hosting the
MCP facade and all renderer dependencies in one container.

## Release Target

The split facade release target is `<= 200 MB` idle memory during a
representative idle window with no render requests. If the final platform
reports memory differently, compare against the pre-split `~0.689 GB` Railway
baseline and record the measurement method.

## Runtime Modes

The facade supports two renderer modes:

| Mode | Environment | Behavior |
| --- | --- | --- |
| In-process | `DIAGRAMS_RENDERER_MODE=in-process` or unset | Existing behavior; facade executes renderers locally. |
| Remote | `DIAGRAMS_RENDERER_MODE=remote` and `DIAGRAMS_RENDERER_URL=<url>` | Facade delegates render work to a renderer service. |

`DIAGRAMS_RENDERER_URL` may be either a full URL such as
`http://diagrams-renderer.railway.internal:8080` or a Railway private domain
such as `diagrams-renderer.railway.internal`; schemeless values are normalized
to `http://...` by the facade.

On Railway, the renderer should bind to IPv6 for private networking:
`RENDERER_HOST=:: RENDERER_PORT=$PORT diagrams-renderer-server`.
If Railway's HTTP healthcheck cannot reach that IPv6 listener, validate the
renderer via facade `/health` and end-to-end render calls instead of a renderer
service healthcheck.

Temporary output delivery supports two stores:

| Store | Environment | Behavior |
| --- | --- | --- |
| Memory | unset `DIAGRAMS_IMAGE_STORE_DIR` | Existing in-process temporary store. |
| File-backed | `DIAGRAMS_IMAGE_STORE_DIR=/path` | Stores temporary output bytes on disk instead of process memory. |

## Rollback

To return to the pre-split behavior, remove `DIAGRAMS_RENDERER_MODE=remote` or
set `DIAGRAMS_RENDERER_MODE=in-process`, then redeploy the original all-in-one
image. Download links can also be returned to memory storage by unsetting
`DIAGRAMS_IMAGE_STORE_DIR`.

## Validation Checklist

- Confirm `/health` returns `200` for the facade.
- Confirm discovery and reference tools work when the renderer service is not running.
- Confirm `render_diagram`, `render_mermaid`, and `render_plantuml` work through remote mode.
- Compare facade idle memory against the `~0.689 GB` baseline after at least one idle window.

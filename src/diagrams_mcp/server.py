import re

from fastmcp import FastMCP
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from starlette.responses import JSONResponse, Response

from diagrams_mcp.image_store import _FORMAT_MAP, image_store
from diagrams_mcp.prompts import prompts_app
from diagrams_mcp.resources import references
from diagrams_mcp.tools.discovery import discovery
from diagrams_mcp.tools.equivalence import equivalence
from diagrams_mcp.tools.mermaid import mermaid
from diagrams_mcp.tools.plantuml import plantuml
from diagrams_mcp.tools.render import render

mcp = FastMCP(
    "diagrams",
    instructions=(
        "Generate diagrams using multiple rendering engines.\n\n"
        "**mingrammer/diagrams** (cloud architecture): "
        "Use search_nodes to find components by keyword (returns import paths), or browse with "
        "list_providers -> list_services -> list_nodes. Read the diagrams://reference/diagram, "
        "diagrams://reference/edge, and diagrams://reference/cluster resources for constructor "
        "options and usage examples. Then render_diagram to produce images.\n\n"
        "**Mermaid** (flowcharts, sequence, class, ER, state, Gantt): "
        "Read diagrams://reference/mermaid for syntax. "
        "Then render_mermaid with a definition string.\n\n"
        "**PlantUML** (sequence, class, component, activity, state, deployment): "
        "Read diagrams://reference/plantuml for syntax. "
        "Then render_plantuml with a definition string.\n\n"
        "**Cross-provider equivalence**: "
        "Use find_equivalent to find equivalent services across providers "
        "(e.g. find_equivalent('EC2', 'gcp')), or list_categories to see all "
        "mapped infrastructure roles.\n\n"
        "**Tool selection**: Use render_diagram for cloud architecture with real provider icons "
        "(AWS, GCP, Azure, K8s, on-prem). Use render_mermaid for flowcharts, sequence diagrams, "
        "ER diagrams, and Gantt charts. Use render_plantuml for UML-heavy diagrams "
        "(class, component, deployment).\n\n"
        "**Workflow**: Always use search_nodes to verify node names and get import paths before "
        "writing render_diagram code. Invalid imports are the most common error.\n\n"
        "**Output options**: All render tools support `format` "
        "(png, svg, pdf — PlantUML: png/svg only) "
        "and `download_link` (returns a temporary URL instead of inline image data)."
    ),
    mask_error_details=True,
)

# Rate limiting — outermost middleware, runs before all sub-app dispatch.
# Token bucket: sustains 2 req/sec, allows bursts up to 5.
mcp.add_middleware(
    RateLimitingMiddleware(
        max_requests_per_second=2.0,
        burst_capacity=5,
    )
)

mcp.mount(render)
mcp.mount(discovery)
mcp.mount(references)
mcp.mount(mermaid)
mcp.mount(plantuml)
mcp.mount(equivalence)
mcp.mount(prompts_app)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/images/{token}", methods=["GET"])
async def serve_image(request):
    token = request.path_params["token"]
    entry = image_store.get(token)
    if entry is None:
        return JSONResponse({"error": "not found or expired"}, status_code=404)
    safe_name = _sanitize_filename(entry.filename)
    fmt_info = _FORMAT_MAP.get(entry.fmt, _FORMAT_MAP["png"])
    return Response(
        content=entry.data,
        media_type=fmt_info["mime"],
        headers={"Content-Disposition": f'attachment; filename="{safe_name}{fmt_info["ext"]}"'},
    )


def _sanitize_filename(name: str) -> str:
    """Sanitize a filename for use in Content-Disposition headers."""
    name = re.sub(r'["\\/\r\n\x00-\x1f]', "", name)
    name = name[:100]
    return name or "image"


def main():
    mcp.run()


if __name__ == "__main__":
    main()

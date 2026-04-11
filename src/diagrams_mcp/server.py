import re

from fastmcp import FastMCP
from starlette.responses import JSONResponse, Response

from diagrams_mcp.image_store import _FORMAT_MAP, image_store
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
        "options and usage examples. Then render_diagram to produce PNG images.\n\n"
        "**Mermaid** (flowcharts, sequence, class, ER, state, Gantt): "
        "Read diagrams://reference/mermaid for syntax. "
        "Then render_mermaid with a definition string.\n\n"
        "**PlantUML** (sequence, class, component, activity, state, deployment): "
        "Read diagrams://reference/plantuml for syntax. "
        "Then render_plantuml with a definition string.\n\n"
        "**Cross-provider equivalence**: "
        "Use find_equivalent to find equivalent services across providers "
        "(e.g. find_equivalent('EC2', 'gcp')), or list_categories to see all "
        "mapped infrastructure roles."
    ),
    mask_error_details=True,
)

mcp.mount(render)
mcp.mount(discovery)
mcp.mount(references)
mcp.mount(mermaid)
mcp.mount(plantuml)
mcp.mount(equivalence)


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

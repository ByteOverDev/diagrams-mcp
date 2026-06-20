import re

from mcp.server.fastmcp.server import FastMCP
from starlette.responses import JSONResponse, Response

from diagrams_mcp.image_store import _FORMAT_MAP, output_store
from diagrams_mcp.prompts import (
    architecture_diagram,
    compare_providers,
    quick_sketch,
    sequence_flow,
)
from diagrams_mcp.resources import (
    cluster_reference,
    diagram_reference,
    edge_reference,
    mermaid_reference,
    plantuml_reference,
)
from diagrams_mcp.tools.discovery import list_nodes, list_providers, list_services, search_nodes
from diagrams_mcp.tools.equivalence import find_equivalent, list_categories
from diagrams_mcp.tools.mermaid import render_mermaid
from diagrams_mcp.tools.plantuml import render_plantuml
from diagrams_mcp.tools.render import render_diagram

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
)

mcp.add_tool(render_diagram, annotations={"readOnlyHint": True}, structured_output=False)
mcp.add_tool(list_providers, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(list_services, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(list_nodes, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(search_nodes, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(find_equivalent, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(list_categories, annotations={"readOnlyHint": True, "idempotentHint": True})
mcp.add_tool(render_mermaid, annotations={"readOnlyHint": True}, structured_output=False)
mcp.add_tool(render_plantuml, annotations={"readOnlyHint": True}, structured_output=False)

mcp.resource("diagrams://reference/diagram", mime_type="text/markdown")(diagram_reference)
mcp.resource("diagrams://reference/edge", mime_type="text/markdown")(edge_reference)
mcp.resource("diagrams://reference/cluster", mime_type="text/markdown")(cluster_reference)
mcp.resource("diagrams://reference/mermaid", mime_type="text/markdown")(mermaid_reference)
mcp.resource("diagrams://reference/plantuml", mime_type="text/markdown")(plantuml_reference)

mcp.prompt(description="Guide the user through building a cloud architecture diagram")(
    architecture_diagram
)
mcp.prompt(description="Guide creation of a sequence or flow diagram")(sequence_flow)
mcp.prompt(description="Walk through multi-cloud service comparison")(compare_providers)
mcp.prompt(
    description=(
        "Minimal-friction path: describe what to visualize and the best engine is"
        " picked automatically"
    )
)(quick_sketch)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse(
        {
            "schemaVersion": 1,
            "label": "Railway",
            "message": "up",
            "color": "green",
        }
    )


@mcp.custom_route("/images/{token}", methods=["GET"])
async def serve_image(request):
    token = request.path_params["token"]
    entry = output_store.get(token)
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
    name = name.encode("ascii", errors="ignore").decode("ascii")
    name = name[:100]
    return name or "image"


def create_test_http_app():
    """Return a fresh HTTP app for tests.

    FastMCP caches a one-shot session manager behind ``streamable_http_app()``;
    TestClient startup/shutdown across multiple tests needs a fresh one.
    """
    mcp._session_manager = None
    return mcp.streamable_http_app()


def main():
    mcp.run()


if __name__ == "__main__":
    main()

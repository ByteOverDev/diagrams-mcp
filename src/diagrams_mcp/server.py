from fastmcp import FastMCP
from starlette.responses import JSONResponse, Response

from diagrams_mcp.image_store import image_store
from diagrams_mcp.resources import references
from diagrams_mcp.tools.discovery import discovery
from diagrams_mcp.tools.render import render

mcp = FastMCP(
    "diagrams",
    instructions=(
        "Generate cloud architecture diagrams using Python's mingrammer/diagrams library. "
        "Use search_nodes to find components by keyword (returns import paths), or browse with "
        "list_providers -> list_services -> list_nodes. Read the diagrams://reference/diagram, "
        "diagrams://reference/edge, and diagrams://reference/cluster resources for constructor "
        "options and usage examples. Then render_diagram to produce PNG images."
    ),
    mask_error_details=True,
)

mcp.mount(render)
mcp.mount(discovery)
mcp.mount(references)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/images/{token}", methods=["GET"])
async def serve_image(request):
    token = request.path_params["token"]
    entry = image_store.get(token)
    if entry is None:
        return JSONResponse({"error": "not found or expired"}, status_code=404)
    return Response(
        content=entry.data,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{entry.filename}.png"'},
    )


def main():
    mcp.run()


if __name__ == "__main__":
    main()

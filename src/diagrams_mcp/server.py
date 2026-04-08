from fastmcp import FastMCP

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


def main():
    mcp.run()


if __name__ == "__main__":
    main()

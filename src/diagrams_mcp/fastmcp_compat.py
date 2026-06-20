import base64

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.server import FastMCP
from mcp.server.fastmcp.utilities.types import Image
from mcp.types import BlobResourceContents, EmbeddedResource


def binary_file(data: bytes, filename: str, mime_type: str) -> EmbeddedResource:
    return EmbeddedResource(
        type="resource",
        resource=BlobResourceContents(
            uri=f"file:///{filename}",
            blob=base64.b64encode(data).decode(),
            mimeType=mime_type,
            name=filename,
        ),
    )


__all__ = ["FastMCP", "Image", "ToolError", "binary_file"]

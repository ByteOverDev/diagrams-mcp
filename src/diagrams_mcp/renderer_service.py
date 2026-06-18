"""HTTP service entry point for the separated renderer."""

import os

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from diagrams_mcp.renderer import render_from_payload


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "up", "service": "diagrams-renderer"})


async def render(request: Request) -> JSONResponse:
    payload = await request.json()
    result = render_from_payload(payload)
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/render", render, methods=["POST"]),
    ]
)


def main() -> None:
    import uvicorn

    host = os.environ.get("RENDERER_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("RENDERER_PORT", "8001")))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()

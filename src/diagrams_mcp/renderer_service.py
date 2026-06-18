"""HTTP service entry point for the separated renderer."""

import asyncio
import json
import os
import socket

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from diagrams_mcp.renderer import render_from_payload


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "up", "service": "diagrams-renderer"})


async def render(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        return JSONResponse(
            {"ok": False, "error": str(exc), "errorType": type(exc).__name__},
            status_code=400,
        )
    result = await asyncio.to_thread(render_from_payload, payload)
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/render", render, methods=["POST"]),
    ]
)


def main() -> None:
    import uvicorn

    host = os.environ.get("RENDERER_HOST", "::")
    port = int(os.environ.get("PORT", os.environ.get("RENDERER_PORT", "8001")))
    if host == "::":
        sockets = _bind_dual_stack_sockets(port)
        config = uvicorn.Config(app, host=host, port=port)
        server = uvicorn.Server(config)
        server.run(sockets=sockets)
        return
    uvicorn.run(app, host=host, port=port)


def _bind_dual_stack_sockets(port: int) -> list[socket.socket]:
    """Bind IPv6 for Railway private DNS and IPv4 for platform healthchecks."""
    sockets: list[socket.socket] = []
    try:
        ipv6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        ipv6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "IPV6_V6ONLY"):
            ipv6.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        ipv6.bind(("::", port))
        ipv6.listen()
        sockets.append(ipv6)

        bound_port = ipv6.getsockname()[1]
        ipv4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ipv4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ipv4.bind(("0.0.0.0", bound_port))
        ipv4.listen()
        sockets.append(ipv4)
    except Exception:
        for sock in sockets:
            sock.close()
        raise
    return sockets


if __name__ == "__main__":
    main()

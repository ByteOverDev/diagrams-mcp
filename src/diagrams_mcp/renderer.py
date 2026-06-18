"""Renderer boundary for in-process and remote diagram rendering."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import site
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastmcp.exceptions import ToolError

from diagrams_mcp.sandbox import run_cli, run_code

RenderKind = Literal["diagram", "mermaid", "plantuml"]
RenderFormat = Literal["png", "svg", "pdf"]

_DEFAULT_TIMEOUT = 25.0
_PUPPETEER_CONFIG = os.environ.get("MERMAID_PUPPETEER_CONFIG", "/etc/mermaid/puppeteer-config.json")
_PLANTUML_JAR = os.environ.get("PLANTUML_JAR", "/opt/plantuml.jar")
_RE_SVG_IMAGE_HREF = re.compile(r'(<image\b[^>]*?xlink:href=")([^"]+\.png)(")')
_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """Serializable render request shared by facade and renderer service."""

    kind: RenderKind
    source: str
    filename: str = "diagram"
    format: RenderFormat = "png"


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Rendered artifact bytes with basic lifecycle metadata."""

    data: bytes
    format: RenderFormat
    renderer: RenderKind
    duration_ms: int


class BaseRenderer:
    """Renderer interface used by MCP tools."""

    def render(self, request: RenderRequest) -> RenderResult:
        raise NotImplementedError


def graphviz_available() -> bool:
    """Return whether Graphviz's dot binary is available in this runtime."""
    return shutil.which("dot") is not None


def graphviz_install_hint() -> str:
    if sys.platform == "darwin":
        return "Install with: brew install graphviz"
    if sys.platform == "win32":
        return (
            "Install with: choco install graphviz  or download from https://graphviz.org/download/"
        )
    return "Install with: apt install graphviz (Debian/Ubuntu) or dnf install graphviz (Fedora)"


class InProcessRenderer(BaseRenderer):
    """Renderer that preserves the original local subprocess behavior."""

    def render(self, request: RenderRequest) -> RenderResult:
        start = time.monotonic()
        _log_render_event("render_dispatch", request, backend="in-process")
        try:
            if request.kind == "diagram":
                data = self._render_diagram(request)
            elif request.kind == "mermaid":
                data = self._render_mermaid(request)
            elif request.kind == "plantuml":
                data = self._render_plantuml(request)
            else:
                raise ToolError(f"Unsupported renderer kind: {request.kind}")
        except Exception as exc:
            _log_render_event(
                "render_failed",
                request,
                backend="in-process",
                duration_ms=int((time.monotonic() - start) * 1000),
                error_type=type(exc).__name__,
            )
            raise
        duration_ms = int((time.monotonic() - start) * 1000)
        _log_render_event(
            "render_completed",
            request,
            backend="in-process",
            duration_ms=duration_ms,
            output_bytes=len(data),
        )
        return RenderResult(
            data=data,
            format=request.format,
            renderer=request.kind,
            duration_ms=duration_ms,
        )

    def _render_diagram(self, request: RenderRequest) -> bytes:
        if not graphviz_available():
            raise ToolError(
                "Graphviz is not installed. The render_diagram tool requires it.\n"
                + graphviz_install_hint()
            )
        tmpdir = run_code(request.source, filename=request.filename, outformat=request.format)
        try:
            outputs = sorted(Path(tmpdir).glob(f"*.{request.format}"))
            if not outputs:
                raise ToolError(
                    "No diagram output produced. "
                    "Make sure your code uses a `with Diagram(...):` block."
                )
            data = outputs[0].read_bytes()
            if request.format == "svg":
                try:
                    return _embed_svg_images(data)
                except (UnicodeDecodeError, OSError) as exc:
                    raise ToolError(f"Failed to embed SVG images: {exc}") from exc
            return data
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _render_mermaid(self, request: RenderRequest) -> bytes:
        cmd = ["mmdc", "-i", "-", "-o", "-", "-e", request.format]
        if os.path.isfile(_PUPPETEER_CONFIG):
            cmd.extend(["-p", _PUPPETEER_CONFIG])
        return run_cli(cmd, input_data=request.source.encode(), timeout=_DEFAULT_TIMEOUT)

    def _render_plantuml(self, request: RenderRequest) -> bytes:
        return run_cli(
            [
                "java",
                "-Djava.awt.headless=true",
                "-Xmx256m",
                "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
                "-jar",
                _PLANTUML_JAR,
                f"-t{request.format}",
                "-pipe",
            ],
            input_data=request.source.encode(),
            timeout=_DEFAULT_TIMEOUT,
        )


class RemoteRenderer(BaseRenderer):
    """HTTP renderer client used by the slim facade."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def render(self, request: RenderRequest) -> RenderResult:
        _log_render_event("render_dispatch", request, backend="remote")
        payload = json.dumps(_request_to_payload(request)).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/render",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.monotonic()
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            _log_render_event(
                "render_failed",
                request,
                backend="remote",
                duration_ms=int((time.monotonic() - start) * 1000),
                error_type="HTTPError",
            )
            raise ToolError(f"Remote renderer failed: {detail}") from exc
        except OSError as exc:
            _log_render_event(
                "render_failed",
                request,
                backend="remote",
                duration_ms=int((time.monotonic() - start) * 1000),
                error_type=type(exc).__name__,
            )
            raise ToolError(f"Remote renderer unavailable: {exc}") from exc

        try:
            decoded = json.loads(body.decode("utf-8"))
            if not decoded.get("ok", False):
                raise ToolError(decoded.get("error", "Remote renderer failed"))
            data = base64.b64decode(decoded["data"])
            fmt = decoded.get("format", request.format)
        except (KeyError, ValueError, TypeError) as exc:
            _log_render_event(
                "render_failed",
                request,
                backend="remote",
                duration_ms=int((time.monotonic() - start) * 1000),
                error_type=type(exc).__name__,
            )
            raise ToolError(f"Remote renderer returned an invalid response: {exc}") from exc
        duration_ms = int((time.monotonic() - start) * 1000)
        _log_render_event(
            "render_completed",
            request,
            backend="remote",
            duration_ms=duration_ms,
            output_bytes=len(data),
        )
        return RenderResult(
            data=data,
            format=fmt,
            renderer=request.kind,
            duration_ms=duration_ms,
        )


def get_renderer() -> BaseRenderer:
    """Return the configured renderer implementation."""
    mode = os.environ.get("DIAGRAMS_RENDERER_MODE", "in-process").strip().lower()
    if mode == "remote":
        url = os.environ.get("DIAGRAMS_RENDERER_URL", "").strip()
        if not url:
            raise ToolError("DIAGRAMS_RENDERER_URL is required when DIAGRAMS_RENDERER_MODE=remote")
        return RemoteRenderer(url)
    return InProcessRenderer()


def _request_to_payload(request: RenderRequest) -> dict[str, str]:
    return {
        "kind": request.kind,
        "source": request.source,
        "filename": request.filename,
        "format": request.format,
    }


def _log_render_event(event: str, request: RenderRequest, **fields: object) -> None:
    payload = {
        "event": event,
        "renderer": request.kind,
        "format": request.format,
        "filename": request.filename,
        **fields,
    }
    _logger.info("render_event %s", json.dumps(payload, sort_keys=True))


def render_from_payload(payload: dict) -> dict:
    """Render from JSON-compatible payload and return a JSON-compatible response."""
    try:
        request = RenderRequest(
            kind=payload["kind"],
            source=payload["source"],
            filename=payload.get("filename", "diagram"),
            format=payload.get("format", "png"),
        )
        result = InProcessRenderer().render(request)
        return {
            "ok": True,
            "data": base64.b64encode(result.data).decode("ascii"),
            "format": result.format,
            "durationMs": result.duration_ms,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "errorType": type(exc).__name__}


def _find_resources_dir() -> Path | None:
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = Path(sp) / "resources"
        if candidate.is_dir():
            return candidate
    return None


def _embed_svg_images(svg_data: bytes) -> bytes:
    resources_dir = _find_resources_dir()
    if resources_dir is None:
        return svg_data

    svg_text = svg_data.decode("utf-8")
    resources_suffix = "/resources/"

    def _replace_href(match: re.Match) -> str:
        prefix, href, suffix = match.group(1), match.group(2), match.group(3)
        idx = href.find(resources_suffix)
        if idx == -1:
            return match.group(0)
        rel_path = href[idx + len(resources_suffix) :]
        try:
            candidate = (resources_dir / rel_path).resolve()
            if not candidate.is_relative_to(resources_dir.resolve()) or not candidate.is_file():
                return match.group(0)
            b64 = base64.b64encode(candidate.read_bytes()).decode("ascii")
        except (OSError, ValueError):
            return match.group(0)
        return f"{prefix}data:image/png;base64,{b64}{suffix}"

    return _RE_SVG_IMAGE_HREF.sub(_replace_href, svg_text).encode("utf-8")

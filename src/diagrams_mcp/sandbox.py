"""Sandboxed execution of diagram rendering code."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from fastmcp.exceptions import ToolError

_SAFE_FILENAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9 _\-\.]{0,99}$")

_WRAPPER = textwrap.dedent("""\
    import os
    os.chdir({tmpdir!r})

    import diagrams
    _orig_init = diagrams.Diagram.__init__

    def _patched_init(self, *a, **kw):
        kw["show"] = False
        kw["outformat"] = {outformat!r}
        fn = kw.get("filename", {filename!r})
        basename = os.path.basename(fn)
        if not basename or os.path.isabs(fn) or os.sep in fn or "/" in fn or "\\\\" in fn:
            basename = {filename!r}
        kw["filename"] = os.path.join({tmpdir!r}, basename)
        _orig_init(self, *a, **kw)

    diagrams.Diagram.__init__ = _patched_init

""")

_MAX_STDERR_LEN = 1600


def run_code(
    code: str, *, filename: str = "diagram", outformat: str = "png", timeout: float = 25.0
) -> Path:
    """Execute diagram code in a subprocess and return the temp directory path.

    The caller is responsible for cleaning up the returned directory
    (e.g. with ``shutil.rmtree``).

    Args:
        code: Complete Python script using the diagrams library.
        filename: Default output filename (without extension).
        timeout: Maximum execution time in seconds.

    Returns:
        Path to the temp directory containing rendered output files.

    Raises:
        ToolError: On syntax errors, runtime errors, or timeout.
    """
    if not _SAFE_FILENAME.fullmatch(filename):
        raise ToolError(
            f"Invalid filename: {filename!r}. "
            "Use only letters, digits, spaces, hyphens, underscores, or dots."
        )

    tmpdir = tempfile.mkdtemp(prefix="diagrams_mcp_")
    script = _WRAPPER.format(tmpdir=tmpdir, filename=filename, outformat=outformat) + code
    script_path = Path(tmpdir) / "_render.py"
    script_path.write_text(script)

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
        "LANG": "C.UTF-8",
    }

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(
            f"Diagram rendering timed out after {timeout:.0f}s. Try simplifying the diagram."
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if len(stderr) > _MAX_STDERR_LEN:
            stderr = "..." + stderr[-_MAX_STDERR_LEN:]
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(f"Diagram code failed:\n{stderr}")

    return Path(tmpdir)


def run_cli(
    cmd: list[str],
    *,
    input_data: bytes | None = None,
    timeout: float = 25.0,
) -> bytes:
    """Run an external CLI tool in a sandboxed subprocess, returning stdout bytes.

    Args:
        cmd: Command and arguments to execute (e.g. ["mmdc", "-i", "-", "-o", "-"]).
        input_data: Optional bytes piped to the process's stdin.
        timeout: Maximum execution time in seconds.

    Returns:
        Raw bytes captured from the process's stdout.

    Raises:
        ToolError: On non-zero exit, timeout, or empty stdout.
    """
    tmpdir = tempfile.mkdtemp(prefix="diagrams_mcp_cli_")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
        "LANG": "C.UTF-8",
    }

    try:
        result = subprocess.run(
            cmd,
            cwd=tmpdir,
            input=input_data,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(
            f"Rendering timed out after {timeout:.0f}s. Try simplifying the diagram."
        ) from exc
    except (FileNotFoundError, OSError) as exc:
        raise ToolError(f"Failed to execute renderer {cmd[0]!r}: {exc}") from exc
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if result.returncode != 0:
        stderr = result.stderr
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr = stderr.strip()
        if len(stderr) > _MAX_STDERR_LEN:
            stderr = "..." + stderr[-_MAX_STDERR_LEN:]
        raise ToolError(f"Rendering failed:\n{stderr}")

    if not result.stdout:
        raise ToolError("Rendering produced no output. Check the diagram definition.")

    return result.stdout

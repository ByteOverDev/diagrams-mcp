"""Sandboxed execution of diagram rendering code."""

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from fastmcp.exceptions import ToolError

_WRAPPER = textwrap.dedent("""\
    import os
    os.chdir({tmpdir!r})

    import diagrams
    _orig_init = diagrams.Diagram.__init__

    def _patched_init(self, *a, **kw):
        kw["show"] = False
        fn = kw.get("filename", {filename!r})
        basename = os.path.basename(fn)
        if not basename or os.path.isabs(fn) or os.sep in fn or "/" in fn or "\\\\" in fn:
            basename = {filename!r}
        kw["filename"] = os.path.join({tmpdir!r}, basename)
        _orig_init(self, *a, **kw)

    diagrams.Diagram.__init__ = _patched_init

""")

_MAX_STDERR_LEN = 1600


def run_code(code: str, *, filename: str = "diagram", timeout: float = 25.0) -> Path:
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
    tmpdir = tempfile.mkdtemp(prefix="diagrams_mcp_")
    script = _WRAPPER.format(tmpdir=tmpdir, filename=filename) + code
    script_path = Path(tmpdir) / "_render.py"
    script_path.write_text(script)

    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
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
    except subprocess.TimeoutExpired:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(
            f"Diagram rendering timed out after {timeout:.0f}s. "
            "Try simplifying the diagram."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if len(stderr) > _MAX_STDERR_LEN:
            stderr = "..." + stderr[-_MAX_STDERR_LEN:]
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(f"Diagram code failed:\n{stderr}")

    return Path(tmpdir)

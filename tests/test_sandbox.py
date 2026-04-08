import pytest
from fastmcp.exceptions import ToolError

from diagrams_mcp.sandbox import run_code


def test_run_code_simple_script():
    """run_code executes a simple Python script and returns a temp directory."""
    tmpdir = run_code("print('hello')")
    try:
        assert tmpdir.is_dir()
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_run_code_syntax_error():
    """run_code raises ToolError with stderr on syntax errors."""
    with pytest.raises(ToolError, match="SyntaxError"):
        run_code("def f(")


def test_run_code_timeout():
    """run_code raises ToolError when the subprocess exceeds the timeout."""
    with pytest.raises(ToolError, match="timed out"):
        run_code("import time; time.sleep(60)", timeout=1)

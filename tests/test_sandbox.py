import tempfile

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


def test_run_code_minimal_env():
    """run_code subprocess inherits only minimal environment variables."""
    import json

    code = "import os, json; print(json.dumps(dict(os.environ)))"
    tmpdir = run_code(code)
    try:
        result_code = "import os, json; json.dump(dict(os.environ), open('env.json','w'))"
        tmpdir2 = run_code(result_code)
        try:
            env = json.loads((tmpdir2 / "env.json").read_text())
            assert "HOME" in env
            assert env["HOME"].startswith(tempfile.gettempdir())
            assert "SECRET_KEY" not in env
        finally:
            import shutil
            shutil.rmtree(tmpdir2, ignore_errors=True)
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

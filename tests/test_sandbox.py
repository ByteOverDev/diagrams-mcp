import tempfile

import pytest
from fastmcp.exceptions import ToolError

from diagrams_mcp.sandbox import run_cli, run_code


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


def test_run_code_rejects_invalid_filename():
    """run_code rejects filenames with unsafe characters."""
    with pytest.raises(ToolError, match="Invalid filename"):
        run_code("print('hello')", filename='"; import os #')

    with pytest.raises(ToolError, match="Invalid filename"):
        run_code("print('hello')", filename="../etc/passwd")

    with pytest.raises(ToolError, match="Invalid filename"):
        run_code("print('hello')", filename="")


def test_run_code_accepts_valid_filenames():
    """run_code accepts reasonable filenames."""
    import shutil

    for name in ["diagram", "my-diagram", "Web_Service_2024", "test.output"]:
        tmpdir = run_code("print('ok')", filename=name)
        try:
            assert tmpdir.is_dir()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


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


def test_run_cli_returns_stdout():
    """run_cli captures and returns stdout bytes."""
    result = run_cli(["printf", "%s", "hello"])
    assert result == b"hello"


def test_run_cli_passes_stdin():
    """run_cli pipes input_data to the process's stdin."""
    result = run_cli(["cat"], input_data=b"from stdin")
    assert result == b"from stdin"


def test_run_cli_timeout():
    """run_cli raises ToolError when the subprocess exceeds the timeout."""
    with pytest.raises(ToolError, match="timed out"):
        run_cli(["sleep", "60"], timeout=1)


def test_run_cli_nonzero_exit():
    """run_cli raises ToolError on non-zero exit code."""
    with pytest.raises(ToolError, match="Rendering failed"):
        run_cli(["false"])


def test_run_cli_empty_stdout():
    """run_cli raises ToolError when subprocess produces no output."""
    with pytest.raises(ToolError, match="no output"):
        run_cli(["true"])


def test_run_cli_minimal_env():
    """run_cli subprocess inherits only minimal environment variables."""
    result = run_cli(["env"])
    env_lines = result.decode().strip().split("\n")
    env_dict = dict(line.split("=", 1) for line in env_lines if "=" in line)
    assert "PATH" in env_dict
    assert "HOME" in env_dict
    assert "SECRET_KEY" not in env_dict

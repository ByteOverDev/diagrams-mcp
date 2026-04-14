"""Sandboxed execution of diagram rendering code."""

import ast
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from fastmcp.exceptions import ToolError

_SAFE_FILENAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9 _\-\.]{0,99}$")

_BLOCKED_MODULES = frozenset(
    {
        "os",
        "subprocess",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "ctypes",
        "shutil",
        "multiprocessing",
        "signal",
        "importlib",
        "code",
        "codeop",
        "pty",
        "pipes",
        "webbrowser",
        "ftplib",
        "smtplib",
        "ssl",
        "xmlrpc",
        "telnetlib",
    }
)


def _blocked_import_name(node: ast.AST) -> str | None:
    """Return the full dotted name if this AST node imports a blocked module, else None."""
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name.split(".")[0] in _BLOCKED_MODULES:
                return alias.name
    elif isinstance(node, ast.ImportFrom) and node.module:
        if node.module.split(".")[0] in _BLOCKED_MODULES:
            return node.module
    return None


def _validate_imports(code: str) -> None:
    """Reject code that imports blocked modules.

    This is a UX layer providing clear error messages — not a security boundary.
    Seccomp (Linux) is the hard backstop for bypass vectors like __import__().
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return  # Let the subprocess report syntax errors with full tracebacks

    for node in ast.walk(tree):
        blocked = _blocked_import_name(node)
        if blocked:
            raise ToolError(
                f"Import of '{blocked}' is not allowed in diagram code. "
                "Only diagrams-related imports are permitted."
            )


_WRAPPER = textwrap.dedent("""\
    import errno as _errno
    import platform as _platform
    try:
        import pyseccomp as _seccomp
        _f = _seccomp.SyscallFilter(_seccomp.ALLOW)
        for _sc in [
            "socket", "connect", "bind", "listen", "accept", "accept4",
            "sendto", "recvfrom", "sendmsg", "recvmsg", "socketpair",
        ]:
            _f.add_rule(_seccomp.ERRNO(_errno.EACCES), _sc)
        _f.load()
        del _f, _sc, _seccomp
    except ImportError:
        if _platform.system() == "Linux":
            raise RuntimeError(
                "pyseccomp is required on Linux for sandbox network blocking "
                "but could not be imported. Install it with: pip install pyseccomp"
            )
    del _errno, _platform

    import sys as _sys
    import resource as _resource
    _resource.setrlimit(_resource.RLIMIT_CPU, (30, 30))
    _resource.setrlimit(_resource.RLIMIT_FSIZE, (50_000_000, 50_000_000))
    if _sys.platform == "linux":
        _resource.setrlimit(_resource.RLIMIT_AS, (512_000_000, 512_000_000))
    del _resource

    import os as _os
    _os.chdir({tmpdir!r})

    import diagrams
    _orig_init = diagrams.Diagram.__init__

    def _patched_init(self, *a,
                      _basename=_os.path.basename,
                      _isabs=_os.path.isabs,
                      _join=_os.path.join,
                      _sep=_os.sep,
                      _orig=_orig_init,
                      **kw):
        kw["show"] = False
        kw["outformat"] = {outformat!r}
        fn = kw.get("filename", {filename!r})
        basename = _basename(fn)
        if not basename or _isabs(fn) or _sep in fn or "/" in fn or "\\\\" in fn:
            basename = {filename!r}
        kw["filename"] = _join({tmpdir!r}, basename)
        _orig(self, *a, **kw)

    diagrams.Diagram.__init__ = _patched_init

    # ── Landlock filesystem sandbox (Linux 5.13+) ──────────────────────
    # Restrict filesystem access to tmpdir (rw) and system paths (ro).
    # Best-effort: silently skipped on non-Linux or kernels without Landlock.
    if _sys.platform == "linux":
        import ctypes as _ctypes
        import platform as _plat

        _NR_landlock_create_ruleset = 444
        _NR_landlock_add_rule       = 445
        _NR_landlock_restrict_self  = 446
        _LANDLOCK_CREATE_RULESET_VERSION = 1
        _LANDLOCK_RULE_PATH_BENEATH      = 1
        _PR_SET_NO_NEW_PRIVS             = 38

        # ABI v1 FS access rights
        _FS_EXECUTE     = 1 << 0
        _FS_WRITE_FILE  = 1 << 1
        _FS_READ_FILE   = 1 << 2
        _FS_READ_DIR    = 1 << 3
        _FS_REMOVE_DIR  = 1 << 4
        _FS_REMOVE_FILE = 1 << 5
        _FS_MAKE_CHAR   = 1 << 6
        _FS_MAKE_DIR    = 1 << 7
        _FS_MAKE_REG    = 1 << 8
        _FS_MAKE_SOCK   = 1 << 9
        _FS_MAKE_FIFO   = 1 << 10
        _FS_MAKE_BLOCK  = 1 << 11
        _FS_MAKE_SYM    = 1 << 12
        _FS_REFER       = 1 << 13   # ABI v2
        _FS_TRUNCATE    = 1 << 14   # ABI v3
        _FS_IOCTL_DEV   = 1 << 15   # ABI v5

        class _RulesetAttr(_ctypes.Structure):
            _fields_ = [("handled_access_fs", _ctypes.c_uint64)]

        class _PathBeneathAttr(_ctypes.Structure):
            _fields_ = [
                ("allowed_access", _ctypes.c_uint64),
                ("parent_fd",      _ctypes.c_int32),
            ]

        def _ll_apply(tmpdir_path):
            if _plat.machine() not in ("x86_64", "aarch64"):
                return
            _libc = _ctypes.CDLL("libc.so.6", use_errno=True)
            _libc.syscall.restype = _ctypes.c_long
            _libc.prctl.restype = _ctypes.c_int

            def _sc(nr, *args):
                ret = _libc.syscall(nr, *args)
                if ret == -1:
                    err = _ctypes.get_errno()
                    raise OSError(err, _os.strerror(err))
                return int(ret)

            # Query ABI version
            abi = _sc(_NR_landlock_create_ruleset,
                      _ctypes.c_void_p(0), 0,
                      _LANDLOCK_CREATE_RULESET_VERSION)

            # Build maximal handled_access_fs for this ABI
            all_rights = (
                _FS_EXECUTE | _FS_WRITE_FILE | _FS_READ_FILE | _FS_READ_DIR
                | _FS_REMOVE_DIR | _FS_REMOVE_FILE
                | _FS_MAKE_CHAR | _FS_MAKE_DIR | _FS_MAKE_REG
                | _FS_MAKE_SOCK | _FS_MAKE_FIFO | _FS_MAKE_BLOCK | _FS_MAKE_SYM
            )
            if abi >= 2: all_rights |= _FS_REFER
            if abi >= 3: all_rights |= _FS_TRUNCATE
            if abi >= 5: all_rights |= _FS_IOCTL_DEV

            # Rights for tmpdir: read + write + create + remove + truncate
            rw_rights = (
                _FS_READ_FILE | _FS_WRITE_FILE | _FS_READ_DIR
                | _FS_REMOVE_DIR | _FS_REMOVE_FILE
                | _FS_MAKE_DIR | _FS_MAKE_REG | _FS_MAKE_SYM
                | _FS_MAKE_FIFO | _FS_EXECUTE
            )
            if abi >= 3: rw_rights |= _FS_TRUNCATE

            # Rights for read-only system paths
            ro_rights = _FS_EXECUTE | _FS_READ_FILE | _FS_READ_DIR

            attr = _RulesetAttr(handled_access_fs=all_rights)
            ruleset_fd = _sc(
                _NR_landlock_create_ruleset,
                _ctypes.byref(attr), _ctypes.sizeof(attr), 0
            )
            try:
                def _add_path_rule(path, rights):
                    if not _os.path.isdir(path):
                        return  # LANDLOCK_RULE_PATH_BENEATH requires a directory fd
                    try:
                        fd = _os.open(path, _os.O_PATH | _os.O_CLOEXEC)
                    except OSError:
                        return  # path doesn't exist or not accessible
                    try:
                        rule = _PathBeneathAttr(allowed_access=rights, parent_fd=fd)
                        _sc(_NR_landlock_add_rule, ruleset_fd,
                            _LANDLOCK_RULE_PATH_BENEATH,
                            _ctypes.byref(rule), 0)
                    finally:
                        _os.close(fd)

                # Allow read+write in tmpdir
                _add_path_rule(tmpdir_path, rw_rights)

                # Allow read-only access to system paths (Python, graphviz, libs)
                for _sp in ["/usr", "/lib", "/lib64", "/etc",
                            "/proc", "/dev"]:
                    _add_path_rule(_sp, ro_rights)
                # Allow read-only access to Python's prefix (e.g. /opt, virtualenvs)
                for _pp in set(_sys.path):
                    if _pp and _os.path.isdir(_pp):
                        _add_path_rule(_pp, ro_rights)
                _add_path_rule(_sys.prefix, ro_rights)
                if _sys.exec_prefix != _sys.prefix:
                    _add_path_rule(_sys.exec_prefix, ro_rights)

                # PR_SET_NO_NEW_PRIVS required before restrict_self
                if _libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
                    err = _ctypes.get_errno()
                    raise OSError(err, _os.strerror(err))

                _sc(_NR_landlock_restrict_self, ruleset_fd, 0)
            finally:
                _os.close(ruleset_fd)

        try:
            _ll_apply({tmpdir!r})
        except OSError as _e:
            import errno as _ll_errno
            if _e.errno not in (_ll_errno.ENOSYS, _ll_errno.EOPNOTSUPP):
                raise
            del _ll_errno
        del _ll_apply, _ctypes, _plat
    del _sys

    # Remove privileged modules from globals so user code cannot access them.
    _blocked_globals = ("os", "shutil", "subprocess", "ctypes", "signal")
    for _name in list(globals()):
        if _name in _blocked_globals:
            del globals()[_name]
    del _os, _orig_init, _blocked_globals, _name

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

    _validate_imports(code)

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

    proc = subprocess.Popen(
        [sys.executable, "-I", str(script_path)],
        cwd=tmpdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(
            f"Diagram rendering timed out after {timeout:.0f}s. Try simplifying the diagram."
        )

    if proc.returncode != 0:
        stderr = stderr.strip()
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
        proc = subprocess.Popen(
            cmd,
            cwd=tmpdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
    except (FileNotFoundError, OSError) as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(f"Failed to execute renderer {cmd[0]!r}: {exc}") from exc

    try:
        stdout, stderr = proc.communicate(input=input_data, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ToolError(f"Rendering timed out after {timeout:.0f}s. Try simplifying the diagram.")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if proc.returncode != 0:
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr = stderr.strip()
        if len(stderr) > _MAX_STDERR_LEN:
            stderr = "..." + stderr[-_MAX_STDERR_LEN:]
        raise ToolError(f"Rendering failed:\n{stderr}")

    if not stdout:
        raise ToolError("Rendering produced no output. Check the diagram definition.")

    return stdout

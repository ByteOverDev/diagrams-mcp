import os
import shutil
from pathlib import Path

import pytest

has_mmdc = pytest.mark.skipif(shutil.which("mmdc") is None, reason="mmdc not installed")

has_graphviz = pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")

_plantuml_jar = Path(os.environ.get("PLANTUML_JAR", "/opt/plantuml.jar"))
has_plantuml = pytest.mark.skipif(
    shutil.which("java") is None or not _plantuml_jar.is_file(),
    reason="java not installed or plantuml.jar not found",
)

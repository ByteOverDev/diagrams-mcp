import shutil

import pytest

has_mmdc = pytest.mark.skipif(shutil.which("mmdc") is None, reason="mmdc not installed")
has_plantuml = pytest.mark.skipif(shutil.which("java") is None, reason="java not installed")

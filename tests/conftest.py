import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir) / "test_project"
        project_root.mkdir()
        yield project_root


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
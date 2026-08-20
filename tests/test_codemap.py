"""Tests for utils.codemap — module scanning and code map generation."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from utils.codemap import (
    codemap_to_markdown,
    generate_codemap,
    save_codemap,
    scan_modules,
)


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal Python project for scanning."""
    # Root file
    (tmp_path / "main.py").write_text('"""Entry point."""\nimport os\n\ndef run(): pass\n')
    # Package
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text('"""Core module."""\nimport json\n\nclass Engine:\n    def start(self): pass\n')
    (pkg / "utils.py").write_text("def helper(): pass\n")
    # Hidden / cache dirs should be excluded
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("x = 1\n")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text("y = 2\n")
    return tmp_path


class TestScanModules:
    def test_finds_python_files(self, sample_project):
        modules = scan_modules(str(sample_project))
        filenames = [m["file"] for m in modules.values()]
        assert any("main.py" in f for f in filenames)
        assert any("core.py" in f for f in filenames)

    def test_excludes_hidden_dirs(self, sample_project):
        modules = scan_modules(str(sample_project))
        for info in modules.values():
            assert ".hidden" not in info["file"]

    def test_excludes_pycache(self, sample_project):
        modules = scan_modules(str(sample_project))
        for info in modules.values():
            assert "__pycache__" not in info["file"]

    def test_extracts_classes(self, sample_project):
        modules = scan_modules(str(sample_project))
        core_mod = [m for m in modules.values() if "core.py" in m["file"]][0]
        assert "Engine" in core_mod["classes"]

    def test_extracts_functions(self, sample_project):
        modules = scan_modules(str(sample_project))
        main_mod = [m for m in modules.values() if "main.py" in m["file"]][0]
        assert "run" in main_mod["functions"]

    def test_extracts_docstrings(self, sample_project):
        modules = scan_modules(str(sample_project))
        main_mod = [m for m in modules.values() if "main.py" in m["file"]][0]
        assert main_mod["docstring"] == "Entry point."

    def test_extracts_imports(self, sample_project):
        modules = scan_modules(str(sample_project))
        main_mod = [m for m in modules.values() if "main.py" in m["file"]][0]
        assert "os" in main_mod["imports"]

    def test_nonexistent_path(self):
        modules = scan_modules("/nonexistent/path")
        assert modules == {}


class TestGenerateCodemap:
    def test_contains_modules(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        assert "modules" in codemap
        assert len(codemap["modules"]) > 0

    def test_stats(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        stats = codemap["stats"]
        assert stats["total_files"] >= 3
        assert stats["total_classes"] >= 1
        assert stats["total_functions"] >= 2

    def test_entry_points(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        assert "streamlit_app.py" in codemap["entry_points"]
        assert "main.py" in codemap["entry_points"]


class TestCodemapToMarkdown:
    def test_returns_string(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        md = codemap_to_markdown(codemap)
        assert isinstance(md, str)

    def test_contains_heading(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        md = codemap_to_markdown(codemap)
        assert "# Code Map" in md

    def test_contains_stats(self, sample_project):
        codemap = generate_codemap(str(sample_project))
        md = codemap_to_markdown(codemap)
        assert "files" in md
        assert "lines" in md


class TestSaveCodemap:
    def test_creates_file(self, sample_project, monkeypatch):
        monkeypatch.chdir(str(sample_project))
        out = save_codemap(str(sample_project / "docs" / "CODEMAP.md"))
        assert os.path.exists(out)

    def test_file_has_content(self, sample_project, monkeypatch):
        monkeypatch.chdir(str(sample_project))
        out = save_codemap(str(sample_project / "docs" / "CODEMAP.md"))
        content = Path(out).read_text()
        assert len(content) > 100

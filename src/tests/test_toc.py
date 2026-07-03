"""
Tests for the `doc toc` subcommand: a tree-like table of contents with a depth
limit, driven by the same structural roles as compilation.
"""

from pathlib import Path

import pytest

from doctor.cli import _run_toc


TEST_PROJECT = (Path(__file__).parent.parent.parent / "docs" / "test-project").resolve()


@pytest.fixture(autouse=True)
def _require_project():
    if not TEST_PROJECT.exists():
        pytest.skip("Test project not available")


def test_toc_shows_parts_chapters_and_subchapter(capsys):
    _run_toc([str(TEST_PROJECT)])
    out = capsys.readouterr().out

    assert "Foundations" in out
    assert "1 Introduction" in out
    assert "3.3 Toy Models" in out  # sub-chapter continues the chapter sequence
    assert "A Mathematical Reference" in out  # appendix


def test_depth_limit_truncates(capsys):
    _run_toc(["-L", "1", str(TEST_PROJECT)])
    out = capsys.readouterr().out

    # Depth 1 shows only the top tier (front matter, Parts, appendix), no chapters.
    assert "Foundations" in out
    assert "1 Introduction" not in out


def test_deeper_depth_reveals_subheadings(capsys):
    _run_toc(["-L", "5", str(TEST_PROJECT)])
    out = capsys.readouterr().out

    assert "The Birth of Quantum Field Theory" in out


def test_missing_path_errors(capsys):
    code = _run_toc(["/no/such/path/here"])
    assert code == 1

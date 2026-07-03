"""
Tests for the .doctor/ project anchor: walk-up discovery, compilation profiles
selected via --as / +document.toml, build-dir placement, and title resolution.
"""

from pathlib import Path

import pytest

from doctor.cli import find_doctor_root, parse_args, read_document_type


TEST_PROJECT = (Path(__file__).parent.parent.parent / "docs" / "test-project").resolve()


@pytest.fixture(autouse=True)
def _require_project():
    if not TEST_PROJECT.exists() or not (TEST_PROJECT / ".doctor").is_dir():
        pytest.skip("Test project with .doctor/ not available")


class TestDoctorRoot:
    def test_walks_up_from_a_deep_subdirectory(self):
        deep = TEST_PROJECT / "II. Frontiers" / "3. Black Holes"
        assert find_doctor_root(deep) == TEST_PROJECT

    def test_returns_none_outside_a_project(self, tmp_path):
        assert find_doctor_root(tmp_path) is None

    def test_reads_default_profile_type(self):
        assert read_document_type(TEST_PROJECT) == "book"


class TestProfileResolution:
    def test_default_profile_is_book(self):
        args = parse_args([str(TEST_PROJECT)])
        assert args.profile == "book"
        names = [p.name for p in args.config_paths]
        assert "book.toml" in names
        assert "+document.toml" in names

    def test_as_selects_article_profile(self):
        args = parse_args([str(TEST_PROJECT), "--as", "article"])
        assert args.profile == "article"
        assert "article.toml" in [p.name for p in args.config_paths]

    def test_build_dir_is_inside_dot_doctor(self):
        args = parse_args([str(TEST_PROJECT)])
        assert args.build_dir == TEST_PROJECT / ".doctor" / "build"

    def test_doctor_root_resolved(self):
        args = parse_args([str(TEST_PROJECT)])
        assert args.doctor_root == TEST_PROJECT


class TestTitleResolution:
    def test_title_flag_captured(self):
        args = parse_args([str(TEST_PROJECT), "--title", "My Title"])
        assert args.title == "My Title"

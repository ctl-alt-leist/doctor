"""
Tests for `doc` target resolution, single-file compilation, and defaults lookup.
"""

import pytest

from doctor.cli import _version_id, parse_args
from doctor.configs.loader import get_defaults_dir, get_user_config_dir
from doctor.discovery import discover_single_file
from doctor.resolve import TargetResolutionError, resolve_target


class TestResolveTarget:
    """Test resolving a path argument to a file or directory."""

    def test_explicit_path_to_file(self, tmp_path):
        """An existing file path is returned directly."""
        target = tmp_path / "note.md"
        target.write_text("# Note\n")

        resolved = resolve_target(str(target))

        assert resolved == target.resolve()

    def test_explicit_path_to_directory(self, tmp_path):
        """An existing directory path is returned directly."""
        target = tmp_path / "Project"
        target.mkdir()

        resolved = resolve_target(str(target))

        assert resolved == target.resolve()

    def test_relative_path_resolves_against_cwd(self, tmp_path, monkeypatch):
        """A relative path is resolved, not fuzzy-matched, against the cwd."""
        chapter = tmp_path / "MyChapter"
        chapter.mkdir()
        monkeypatch.chdir(tmp_path)

        resolved = resolve_target("MyChapter")

        assert resolved == chapter.resolve()

    def test_missing_path_raises(self, tmp_path, monkeypatch):
        """A path that does not exist raises — no downward name search."""
        # A directory named so a former fuzzy match ("Chap") would have found it.
        (tmp_path / "sub" / "Chapter").mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(TargetResolutionError, match="No such file or directory"):
            resolve_target("Chapter")


class TestVersionId:
    """Test parsing the v-prefixed version identifier."""

    def test_valid_v_prefixed(self):
        assert _version_id("v1") == 1
        assert _version_id("v42") == 42

    def test_bare_integer_rejected(self):
        """A bare number is no longer accepted; the 'v' is required."""
        import argparse

        with pytest.raises(argparse.ArgumentTypeError, match="expected e.g. 'v1'"):
            _version_id("1")

    def test_garbage_rejected(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            _version_id("vabc")


class TestDiscoverSingleFile:
    """Test building a document structure from a single file."""

    def test_single_file_structure(self, tmp_path):
        """A lone markdown file yields a one-file structure rooted at its parent."""
        note = tmp_path / "note.md"
        note.write_text("# Title\n\nBody.\n")

        structure = discover_single_file(note)

        assert structure.total_files == 1
        assert structure.files[0].name == "note.md"
        assert structure.project_path == tmp_path.resolve()

    def test_non_markdown_rejected(self, tmp_path):
        """A non-markdown file is rejected."""
        other = tmp_path / "data.txt"
        other.write_text("nope")

        with pytest.raises(ValueError, match="Not a markdown file"):
            discover_single_file(other)

    def test_missing_file_rejected(self, tmp_path):
        """A missing file is rejected."""
        with pytest.raises(FileNotFoundError):
            discover_single_file(tmp_path / "absent.md")


class TestSingleFileCliArgs:
    """Test CLI argument resolution for single-file targets."""

    def test_output_defaults_to_sibling_pdf(self, tmp_path, monkeypatch):
        """A single-file target defaults its output to a sibling PDF."""
        note = tmp_path / "note.md"
        note.write_text("# Note\n")
        monkeypatch.chdir(tmp_path)

        args = parse_args(["note.md"])

        assert args.is_single_file is True
        assert args.target_path == note.resolve()
        assert args.output_path == note.with_suffix(".pdf").resolve()
        # The base directory anchors config and build lookups.
        assert args.project_path == tmp_path.resolve()

    def test_directory_target_keeps_named_pdf(self, tmp_path, monkeypatch):
        """A directory target keeps the <project-name>.pdf default."""
        project = tmp_path / "Project"
        project.mkdir()
        monkeypatch.chdir(tmp_path)

        args = parse_args(["Project"])

        assert args.is_single_file is False
        assert args.output_path == (project / "Project.pdf").resolve()


class TestDefaultsLookup:
    """Test default configuration directory resolution."""

    def test_doctor_home_override(self, tmp_path, monkeypatch):
        """DOCTOR_HOME redirects both the user config dir and defaults lookup."""
        defaults = tmp_path / "defaults"
        defaults.mkdir()
        monkeypatch.setenv("DOCTOR_HOME", str(tmp_path))

        assert get_user_config_dir() == tmp_path.resolve()
        assert get_defaults_dir() == defaults.resolve()

    def test_falls_back_to_repo_defaults(self, monkeypatch, tmp_path):
        """With no user defaults present, the repo's configs/defaults is used."""
        # Point DOCTOR_HOME at an empty dir so the user-level candidate misses.
        monkeypatch.setenv("DOCTOR_HOME", str(tmp_path))

        defaults_dir = get_defaults_dir()

        assert defaults_dir.name == "defaults"
        assert (defaults_dir / "document.toml").exists()

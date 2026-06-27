"""
Tests for `doc` target resolution, single-file compilation, and defaults lookup.
"""

import pytest

from doctor.cli import parse_args
from doctor.configs.loader import get_defaults_dir, get_user_config_dir
from doctor.discovery import discover_single_file
from doctor.resolve import TargetResolutionError, resolve_target


class TestResolveTarget:
    """Test resolving a query string to a file or directory."""

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

    def test_find_directory_by_name(self, tmp_path):
        """A bare directory name is located by searching downward."""
        chapter = tmp_path / "sub" / "MyChapter"
        chapter.mkdir(parents=True)

        resolved = resolve_target("MyChapter", search_root=tmp_path)

        assert resolved == chapter.resolve()

    def test_find_file_by_name_via_extension_pattern(self, tmp_path):
        """A bare filename matches through the '<name>.*' pattern."""
        note = tmp_path / "notes" / "intro.md"
        note.parent.mkdir(parents=True)
        note.write_text("# Intro\n")

        resolved = resolve_target("intro", search_root=tmp_path)

        assert resolved == note.resolve()

    def test_no_match_raises(self, tmp_path):
        """A query with no match raises a resolution error."""
        with pytest.raises(TargetResolutionError, match="No file or directory"):
            resolve_target("nonexistent", search_root=tmp_path)

    def test_ambiguous_match_raises(self, tmp_path):
        """A name matching more than one target is ambiguous."""
        (tmp_path / "a" / "Foo").mkdir(parents=True)
        (tmp_path / "b" / "Foo").mkdir(parents=True)

        with pytest.raises(TargetResolutionError, match="Multiple matches"):
            resolve_target("Foo", search_root=tmp_path)

    def test_depth_limits_search(self, tmp_path):
        """A target deeper than the depth limit is not found."""
        deep = tmp_path / "one" / "two" / "three" / "Deep"
        deep.mkdir(parents=True)

        with pytest.raises(TargetResolutionError):
            resolve_target("Deep", depth=2, search_root=tmp_path)


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

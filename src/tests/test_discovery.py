"""
Test file for discovery module
"""

import os
import tempfile
from pathlib import Path

import pytest

from doctor.discovery import (
    DocIgnoreHandler,
    DocumentStructure,
    FileDiscovery,
    MarkdownFile,
    discover_project_files,
    find_files_by_pattern,
    get_file_extensions,
    get_structure_stats,
    validate_project_structure,
)


class TestMarkdownFile:
    """Test MarkdownFile model functionality."""

    def test_markdown_file_model(self):
        """Test MarkdownFile Pydantic model."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test\n\nThis is a test.")
            temp_path = Path(f.name)

        try:
            # Test model creation
            md_file = MarkdownFile(path=temp_path, relative_path=Path("test.md"), name="test.md", parent_dir="docs")

            # Test computed fields
            assert md_file.stem == temp_path.stem
            assert md_file.suffix == ".md"

            # Test content loading
            content = md_file.load_content()
            assert "# Test" in content
            assert md_file.content == content  # Should be cached

            # Test that paths are resolved
            assert md_file.path.is_absolute()

        finally:
            # Clean up
            os.unlink(temp_path)

    def test_content_loading_fallback(self):
        """Test content loading with encoding fallback."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False) as f:
            # Write non-UTF8 content
            f.write(b"# Test with \xff\xfe special chars")
            temp_path = Path(f.name)

        try:
            md_file = MarkdownFile(path=temp_path, relative_path=Path("test.md"), name="test.md", parent_dir="")

            # Should handle encoding issues
            content = md_file.load_content()
            assert "# Test" in content

        finally:
            os.unlink(temp_path)


class TestDocumentStructure:
    """Test DocumentStructure model functionality."""

    def test_document_structure_model(self):
        """Test DocumentStructure Pydantic model."""
        # Create some mock files
        file1 = MarkdownFile(
            path=Path("/fake/path1.md"), relative_path=Path("chapter1/intro.md"), name="intro.md", parent_dir="chapter1"
        )

        file2 = MarkdownFile(
            path=Path("/fake/path2.md"),
            relative_path=Path("chapter1/conclusion.md"),
            name="conclusion.md",
            parent_dir="chapter1",
        )

        file3 = MarkdownFile(
            path=Path("/fake/path3.md"), relative_path=Path("appendix.md"), name="appendix.md", parent_dir=""
        )

        files = [file1, file2, file3]
        directories = {"chapter1": [file1, file2], "": [file3]}

        # Test model creation
        structure = DocumentStructure(
            files=files, directories=directories, total_files=3, project_path=Path("/fake/project")
        )

        # Test methods
        assert len(structure.get_ordered_files()) == 3
        assert len(structure.get_files_by_directory("chapter1")) == 2
        assert len(structure.get_files_by_directory("")) == 1
        assert len(structure.get_files_by_directory("nonexistent")) == 0

        # Test directory names sorting
        dir_names = structure.get_directory_names()
        assert isinstance(dir_names, list)
        assert "chapter1" in dir_names

    def test_natural_sorting(self):
        """Test natural sorting functionality."""
        structure = DocumentStructure(
            files=[],
            directories={"1. First": [], "10. Tenth": [], "2. Second": [], "chapter1": [], "appendix": []},
            total_files=0,
            project_path=Path("/fake"),
        )

        sorted_dirs = structure.get_directory_names()
        # Should sort naturally: 1, 2, 10, then alphabetically
        assert sorted_dirs.index("1. First") < sorted_dirs.index("2. Second")
        assert sorted_dirs.index("2. Second") < sorted_dirs.index("10. Tenth")


class TestDocIgnoreHandler:
    """Test DocIgnoreHandler functionality."""

    def test_docignore_handler(self):
        """Test DocIgnoreHandler functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create .docignore file
            docignore_content = """
# Test patterns
*.tmp
build/
_private
test_*.py
"""
            with open(temp_path / ".docignore", "w") as f:
                f.write(docignore_content)

            handler = DocIgnoreHandler(temp_path)

            # Test underscore files (always ignored)
            assert handler.should_ignore(temp_path / "_private", temp_path)
            assert handler.should_ignore(temp_path / "_figures", temp_path)

            # Test pattern matching
            assert handler.should_ignore(temp_path / "file.tmp", temp_path)

            # Create build directory to test directory pattern
            (temp_path / "build").mkdir()
            assert handler.should_ignore(temp_path / "build", temp_path)

            assert handler.should_ignore(temp_path / "test_something.py", temp_path)

            # Test files that should not be ignored
            assert not handler.should_ignore(temp_path / "file.md", temp_path)
            assert not handler.should_ignore(temp_path / "docs", temp_path)

    def test_docignore_without_file(self):
        """Test DocIgnoreHandler when no .docignore exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            handler = DocIgnoreHandler(temp_path)

            # Only underscore files should be ignored
            assert handler.should_ignore(temp_path / "_private", temp_path)
            assert not handler.should_ignore(temp_path / "normal.md", temp_path)

    def test_readme_is_ignored(self):
        """README files are project documentation, never manuscript content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            handler = DocIgnoreHandler(temp_path)

            # README is ignored at any casing, including inside subdirectories
            assert handler.should_ignore(temp_path / "README.md", temp_path)
            assert handler.should_ignore(temp_path / "readme.md", temp_path)
            assert handler.should_ignore(temp_path / "1. Introduction" / "README.md", temp_path)

            # A file that merely contains "readme" in its name is still content
            assert not handler.should_ignore(temp_path / "readme-notes.md", temp_path)

    def test_plus_and_underscore_prefixes_excluded(self):
        """Both auxiliary (+) and scratch (_) prefixes are excluded from the content sweep."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            handler = DocIgnoreHandler(temp_path)

            # Auxiliary "+" — assets and sub-documents (kept in versions, but not content)
            assert handler.should_ignore(temp_path / "+figures", temp_path)
            assert handler.should_ignore(temp_path / "+papers", temp_path)
            assert handler.should_ignore(temp_path / "+references.toml", temp_path)

            # Scratch "_"
            assert handler.should_ignore(temp_path / "_drafts", temp_path)

            # Ordinary content is not excluded
            assert not handler.should_ignore(temp_path / "1. Introduction", temp_path)


class TestFileDiscovery:
    """Test FileDiscovery functionality."""

    def test_file_discovery_integration(self):
        """Test the complete file discovery process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test directory structure
            (temp_path / "chapter1").mkdir()
            (temp_path / "chapter2").mkdir()
            (temp_path / "_figures").mkdir()  # Should be ignored

            # Create test files
            test_files = [
                "chapter1/1. intro.md",
                "chapter1/2. theory.md",
                "chapter2/1. methods.md",
                "chapter2/2. results.md",
                "conclusion.md",
                "_figures/plot.png",  # Should be ignored
                "notes.txt",  # Should be ignored (not markdown)
            ]

            for file_path in test_files:
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(f"# {file_path}\n\nContent of {file_path}")

            # Test discovery
            discovery = FileDiscovery(temp_path)
            structure = discovery.discover_files()

            # Should find 5 markdown files (ignoring _figures and .txt)
            assert structure.total_files == 5
            assert len(structure.directories) == 3  # chapter1, chapter2, root

            # Test directory contents
            assert len(structure.get_files_by_directory("chapter1")) == 2
            assert len(structure.get_files_by_directory("chapter2")) == 2
            assert len(structure.get_files_by_directory("")) == 1  # conclusion.md

            # Test file ordering (should be alphabetical with natural sorting)
            chapter1_files = structure.get_files_by_directory("chapter1")
            assert chapter1_files[0].name == "1. intro.md"
            assert chapter1_files[1].name == "2. theory.md"

    def test_discover_project_files_function(self):
        """Test the main discover_project_files function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a simple structure (avoid README, which is ignored by design)
            (temp_path / "docs").mkdir()

            with open(temp_path / "intro.md", "w") as f:
                f.write("# Intro")

            with open(temp_path / "docs" / "guide.md", "w") as f:
                f.write("# Guide")

            # Test the main function
            structure = discover_project_files(temp_path)

            assert structure.total_files == 2
            assert structure.project_path == temp_path.resolve()

    def test_error_handling(self):
        """Test error handling in file discovery."""
        # Test non-existent path
        with pytest.raises(FileNotFoundError):
            FileDiscovery(Path("/nonexistent/path"))

        # Test file instead of directory
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(NotADirectoryError):
                FileDiscovery(Path(f.name))

    def test_validate_project_structure(self):
        """Test project structure validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with no markdown files
            with pytest.raises(ValueError, match="No markdown files found"):
                validate_project_structure(temp_path)

            # Test with markdown files
            with open(temp_path / "test.md", "w") as f:
                f.write("# Test")

            structure = validate_project_structure(temp_path)
            assert structure.total_files == 1


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_structure_stats(self):
        """Test structure statistics calculation."""
        # Create mock structure
        files = [
            MarkdownFile(path=Path("/f1.md"), relative_path=Path("f1.md"), name="f1.md", parent_dir=""),
            MarkdownFile(path=Path("/d1/f2.md"), relative_path=Path("d1/f2.md"), name="f2.md", parent_dir="d1"),
            MarkdownFile(path=Path("/d1/f3.md"), relative_path=Path("d1/f3.md"), name="f3.md", parent_dir="d1"),
        ]

        structure = DocumentStructure(
            files=files,
            directories={"": [files[0]], "d1": [files[1], files[2]]},
            total_files=3,
            project_path=Path("/fake"),
        )

        stats = get_structure_stats(structure)

        assert stats["total_files"] == 3
        assert stats["total_directories"] == 2
        assert stats["files_in_root"] == 1
        assert stats["largest_directory"] == 2
        assert stats["deepest_nesting"] == 1

    def test_find_files_by_pattern(self):
        """Test pattern-based file searching."""
        files = [
            MarkdownFile(path=Path("/intro.md"), relative_path=Path("intro.md"), name="intro.md", parent_dir=""),
            MarkdownFile(
                path=Path("/conclusion.md"), relative_path=Path("conclusion.md"), name="conclusion.md", parent_dir=""
            ),
            MarkdownFile(
                path=Path("/chapter1/introduction.md"),
                relative_path=Path("chapter1/introduction.md"),
                name="introduction.md",
                parent_dir="chapter1",
            ),
        ]

        structure = DocumentStructure(files=files, directories={}, total_files=3, project_path=Path("/fake"))

        # Find files with "intro" in name
        intro_files = find_files_by_pattern(structure, r"intro")
        assert len(intro_files) == 2
        assert any(f.name == "intro.md" for f in intro_files)
        assert any(f.name == "introduction.md" for f in intro_files)

    def test_get_file_extensions(self):
        """Test file extension counting."""
        files = [
            MarkdownFile(path=Path("/f1.md"), relative_path=Path("f1.md"), name="f1.md", parent_dir=""),
            MarkdownFile(path=Path("/f2.md"), relative_path=Path("f2.md"), name="f2.md", parent_dir=""),
            MarkdownFile(
                path=Path("/f3.markdown"), relative_path=Path("f3.markdown"), name="f3.markdown", parent_dir=""
            ),
        ]

        structure = DocumentStructure(files=files, directories={}, total_files=3, project_path=Path("/fake"))

        extensions = get_file_extensions(structure)

        assert extensions[".md"] == 2
        assert extensions[".markdown"] == 1

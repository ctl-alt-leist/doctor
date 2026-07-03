"""
Tests for chapter title-page detection.

A chapter is an arabic-numbered directory (``1. Introduction``). The first file
inside such a directory opens a chapter title page carrying the cleaned
directory name; files in the root or in non-chapter directories do not.
"""

from pathlib import Path

import pytest

from doctor.discovery import discover_project_files
from doctor.ingest.content import ContentIngestion
from doctor.ingest.structure import StructureAnalysis, _is_chapter_dir


TEST_PROJECT = (Path(__file__).parent.parent.parent / "docs" / "test-project").resolve()


class TestIsChapterDir:
    """The arabic-numbered-directory predicate."""

    def test_arabic_numbered_dirs_are_chapters(self):
        assert _is_chapter_dir("1. Introduction")
        assert _is_chapter_dir("3. Black Holes")
        assert _is_chapter_dir("10. Later Chapter")

    def test_front_matter_part_and_appendix_are_not_chapters(self):
        assert not _is_chapter_dir("0. Front Matter")  # front matter, not a chapter
        assert not _is_chapter_dir("I. Foundations")  # Part
        assert not _is_chapter_dir("ii. Preface")  # front matter
        assert not _is_chapter_dir("A. Papers")  # appendix
        assert not _is_chapter_dir("Introduction")  # unprefixed


class TestChapterTitlePages:
    """Chapter detection over the real test project."""

    def _analyze(self):
        if not TEST_PROJECT.exists():
            pytest.skip(f"Test project not found at {TEST_PROJECT}")

        file_structure = discover_project_files(TEST_PROJECT)
        content_ingestion = ContentIngestion()
        parsed_files = [content_ingestion.ingest_file(md) for md in file_structure.files]

        analyzer = StructureAnalysis(project_root=TEST_PROJECT)

        return analyzer.analyze_files(parsed_files)

    def test_each_numbered_chapter_opens_a_title_page(self):
        structure = self._analyze()

        openers = {
            file_struct.chapter_title
            for file_struct in structure.files
            if file_struct.is_first_in_chapter and file_struct.chapter_title
        }

        assert openers == {"Introduction", "Quantum Field Theory", "Black Holes"}

    def test_title_page_only_on_first_file_of_a_chapter(self):
        structure = self._analyze()

        first_flags = [f.is_first_in_chapter for f in structure.files if f.chapter_title == "Introduction"]

        # Introduction has two files; exactly one opens the title page.
        assert first_flags.count(True) == 1
        assert first_flags.count(False) == 1

    def test_root_readme_is_not_document_content(self):
        structure = self._analyze()

        # README.md is ignored, so nothing sits at the project root and every
        # discovered file belongs to a chapter directory.
        for file_struct in structure.files:
            assert file_struct.file_path.name.lower() != "readme.md"
            assert file_struct.file_path.parent != TEST_PROJECT
            assert file_struct.chapter_title is not None

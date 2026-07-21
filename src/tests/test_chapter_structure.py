"""
Tests for document structure derived from the file tree (ingest/roles.py).

The test project exercises the full structural vocabulary: a front-matter file,
two Parts, chapters, a chapter-within-a-chapter, and an appendix.
"""

from pathlib import Path

import pytest

from doctor.discovery import discover_project_files
from doctor.ingest.content import ContentIngestion
from doctor.ingest.roles import Role, assign_roles, file_tiers, structural_sort_key
from doctor.ingest.structure import StructureAnalysis


TEST_PROJECT = (Path(__file__).parent.parent.parent / "docs" / "test-project").resolve()


class TestRoleAssignment:
    """Directory classification, including the tricky contextual cases."""

    def test_parts_chapters_subchapters(self):
        dirs = [
            "I. Foundations",
            "I. Foundations/1. Introduction",
            "II. Frontiers/3. Black Holes",
            "II. Frontiers/3. Black Holes/3. Toy Models",
        ]
        roles = assign_roles(dirs)

        assert roles["I. Foundations"] == Role.PART
        assert roles["I. Foundations/1. Introduction"] == Role.CHAPTER
        assert roles["II. Frontiers/3. Black Holes"] == Role.CHAPTER
        assert roles["II. Frontiers/3. Black Holes/3. Toy Models"] == Role.SUBCHAPTER

    def test_single_letter_is_appendix_not_part(self):
        # "A" is not a Roman letter, so it is an appendix even beside Roman Parts.
        roles = assign_roles(["I. Foundations", "II. Frontiers", "A. Mathematical Reference"])
        assert roles["A. Mathematical Reference"] == Role.APPENDIX

    def test_roman_single_letter_appendix_without_part_sibling(self):
        # "C." is Roman-ambiguous; with no multi-letter Roman Part sibling it is an appendix.
        roles = assign_roles(["A. Papers", "B. Articles", "C. Readings"])
        assert roles["C. Readings"] == Role.APPENDIX

    def test_roman_single_letter_is_part_with_part_sibling(self):
        roles = assign_roles(["I. Foundations", "II. Frontiers"])
        assert roles["I. Foundations"] == Role.PART

    def test_front_matter_and_zero(self):
        roles = assign_roles(["0. Front Matter", "i. Prologue"])
        assert roles["0. Front Matter"] == Role.FRONT_MATTER
        assert roles["i. Prologue"] == Role.FRONT_MATTER

    def test_lowercase_letter_is_appendix(self):
        # Lowercase labels a., b. are appendices; the large-value roman letters
        # c., d. (100, 500) never number front matter, so they are appendices too.
        roles = assign_roles(["a. Path Integral", "b. Notation", "c. Tables", "d. Data"])
        assert roles["a. Path Integral"] == Role.APPENDIX
        assert roles["b. Notation"] == Role.APPENDIX
        assert roles["c. Tables"] == Role.APPENDIX
        assert roles["d. Data"] == Role.APPENDIX

    def test_lowercase_small_roman_is_front_matter(self):
        # i., v., x. are small romans a preface can reach, so they stay front matter.
        roles = assign_roles(["i. Preface", "v. Notes", "x. Index"])
        assert roles["i. Preface"] == Role.FRONT_MATTER
        assert roles["v. Notes"] == Role.FRONT_MATTER
        assert roles["x. Index"] == Role.FRONT_MATTER


class TestOrdering:
    """Front matter sorts first, the numbered body next, appendices last."""

    def _order(self, files, dirs=None):
        roles = assign_roles(dirs or [])
        return sorted(files, key=lambda f: structural_sort_key(f, roles))

    def test_appendix_file_sorts_after_numbered(self):
        # The reported bug: a lowercase appendix file jumped ahead of the chapters.
        files = ["a. The Path Integral.md", "2. Two.md", "1. One.md", "3. Three.md"]
        assert self._order(files) == [
            "1. One.md",
            "2. Two.md",
            "3. Three.md",
            "a. The Path Integral.md",
        ]

    def test_front_matter_body_appendix_order(self):
        files = ["b. B.md", "1. One.md", "ii. Intro.md", "a. A.md", "i. Preface.md", "2. Two.md"]
        assert self._order(files) == [
            "i. Preface.md",
            "ii. Intro.md",
            "1. One.md",
            "2. Two.md",
            "a. A.md",
            "b. B.md",
        ]

    def test_appendix_labels_order_alphabetically(self):
        # c., d. must order as the 3rd and 4th appendix, not by roman value (100, 500).
        files = ["e. E.md", "a. A.md", "d. D.md", "b. B.md", "c. C.md"]
        assert self._order(files) == ["a. A.md", "b. B.md", "c. C.md", "d. D.md", "e. E.md"]

    def test_uppercase_appendix_dir_sorts_after_chapters(self):
        dirs = ["1. Intro", "A. Reference"]
        files = ["A. Reference/1. Tables.md", "1. Intro/1. Start.md"]
        assert self._order(files, dirs) == ["1. Intro/1. Start.md", "A. Reference/1. Tables.md"]

    def test_root_appendix_file_marked_appendix(self):
        tiers = file_tiers("a. The Path Integral.md", assign_roles([]))
        assert tiers.is_appendix is True
        assert tiers.is_front_matter is False


class TestFileTiers:
    """Heading offsets exclude Parts and count chapter-like nesting."""

    def test_offsets(self):
        dirs = [
            "I. Foundations",
            "I. Foundations/1. Introduction",
            "II. Frontiers/3. Black Holes",
            "II. Frontiers/3. Black Holes/3. Toy Models",
            "A. Mathematical Reference",
        ]
        roles = assign_roles(dirs)

        # Part + Chapter -> one bump (the Part does not add a level).
        assert file_tiers("I. Foundations/1. Introduction/1. Historical Context.md", roles).heading_offset == 1
        # Part + Chapter + Sub-chapter -> two bumps.
        sub = file_tiers("II. Frontiers/3. Black Holes/3. Toy Models/1. Two-Dimensional Gravity.md", roles)
        assert sub.heading_offset == 2
        assert sub.subchapter_title == "Toy Models"
        # Appendix behaves like a chapter tier.
        appx = file_tiers("A. Mathematical Reference/1. Useful Integrals.md", roles)
        assert appx.heading_offset == 1
        assert appx.is_appendix


class TestStructureOverProject:
    """Structural placement of the real test project's files."""

    def _analyze(self):
        if not TEST_PROJECT.exists():
            pytest.skip(f"Test project not found at {TEST_PROJECT}")
        file_structure = discover_project_files(TEST_PROJECT)
        parsed = [ContentIngestion().ingest_file(md) for md in file_structure.files]

        return StructureAnalysis(project_root=TEST_PROJECT).analyze_files(parsed)

    def test_parts_open_dividers(self):
        structure = self._analyze()
        parts = {f.part_title for f in structure.files if f.is_first_in_part}
        assert parts == {"Foundations", "Frontiers"}

    def test_chapters_open_title_pages(self):
        structure = self._analyze()
        chapters = {f.chapter_title for f in structure.files if f.is_first_in_chapter}
        # Three numbered chapters plus the appendix directory (title-paged like a chapter).
        assert chapters == {"Introduction", "Quantum Field Theory", "Black Holes", "Mathematical Reference"}

    def test_subchapter_opens_once(self):
        structure = self._analyze()
        subs = [f.subchapter_title for f in structure.files if f.is_first_in_subchapter]
        assert subs == ["Toy Models"]

    def test_front_matter_detected(self):
        structure = self._analyze()
        front = [f for f in structure.files if f.is_front_matter_tier]
        assert len(front) == 1
        assert front[0].is_first_in_part is False
        assert front[0].chapter_title is None

    def test_readme_still_excluded(self):
        structure = self._analyze()
        for f in structure.files:
            assert f.file_path.name.lower() != "readme.md"

    def test_plus_auxiliaries_excluded_from_main_document(self):
        structure = self._analyze()
        # The +papers/ sub-document and any +-prefixed path are not swept into the main doc.
        for f in structure.files:
            assert not any(part.startswith("+") for part in f.file_path.parts)

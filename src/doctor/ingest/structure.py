"""
Structure Analysis (H) → Document Structure (N)

Builds hierarchical document structure from parsed content:
- Table of contents generation
- Section numbering and hierarchy
- Document outline and navigation
- Cross-document structure relationships
"""

from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional

from doctor.ingest.roles import Role, assign_roles, file_tiers
from doctor.models.content import ParsedContent, Section
from doctor.models.structure import (
    DocumentOutline,
    DocumentStructure,
    FileStructure,
    TocEntry,
)


def _directory_set(parsed_files: List[ParsedContent], project_root: Path) -> List[str]:
    """Every directory (at every level) that holds a file, as POSIX paths relative to the root."""
    dirs: set[str] = set()
    for parsed_content in parsed_files:
        try:
            relative = parsed_content.source_file.path.relative_to(project_root)
        except ValueError:
            continue
        parts = relative.parent.parts
        for depth in range(1, len(parts) + 1):
            dirs.add(str(PurePosixPath(*parts[:depth])))

    return sorted(dirs)


def _relative_posix(parsed_content: ParsedContent, project_root: Path) -> Optional[str]:
    """A file's POSIX path relative to the project root, or None if outside it."""
    try:
        return parsed_content.source_file.path.relative_to(project_root).as_posix()
    except ValueError:
        return None


class StructureAnalysis:
    """
    Structure Analysis processor (H in architecture diagram).

    Converts ParsedContent into hierarchical DocumentStructure.
    """

    def __init__(self, numbering_style: str = "hierarchical", project_root: Optional[Path] = None):
        """
        Initialize structure analyzer.

        Args:
            numbering_style: "hierarchical" (1.1.1) or "flat" (1, 2, 3) or "none"
            project_root: Root directory of the project (for calculating directory depth)
        """
        self.numbering_style = numbering_style
        self.project_root = project_root
        self.section_counters: Dict[int, int] = {}  # level -> counter

    def analyze_files(self, parsed_files: List[ParsedContent]) -> DocumentStructure:
        """
        Analyze multiple parsed files to create complete document structure.

        Args:
            parsed_files: List of ParsedContent objects

        Returns:
            DocumentStructure: Complete hierarchical structure
        """
        file_structures = []

        # Reset counters for global numbering
        self._reset_counters()

        # Assign a structural role to every directory once, then place each file.
        roles = assign_roles(_directory_set(parsed_files, self.project_root)) if self.project_root else {}

        # Track which tiers have already opened, so a divider fires only once.
        seen_parts: set[str] = set()
        seen_chapters: set[str] = set()
        seen_subchapters: set[str] = set()

        for parsed_content in parsed_files:
            rel = _relative_posix(parsed_content, self.project_root) if self.project_root else None
            tiers = file_tiers(rel, roles) if rel is not None else None

            file_struct = self._analyze_single_file(parsed_content, tiers.heading_offset if tiers else 0)

            if tiers is not None:
                file_struct.part_title = tiers.part_title
                file_struct.chapter_title = tiers.chapter_title
                file_struct.subchapter_title = tiers.subchapter_title
                file_struct.is_front_matter_tier = tiers.is_front_matter
                file_struct.is_appendix_tier = tiers.is_appendix

                if tiers.part_key and tiers.part_key not in seen_parts:
                    file_struct.is_first_in_part = True
                    seen_parts.add(tiers.part_key)
                if tiers.chapter_key and tiers.chapter_key not in seen_chapters:
                    file_struct.is_first_in_chapter = True
                    seen_chapters.add(tiers.chapter_key)
                if tiers.subchapter_key and tiers.subchapter_key not in seen_subchapters:
                    file_struct.is_first_in_subchapter = True
                    seen_subchapters.add(tiers.subchapter_key)

            file_structures.append(file_struct)

        # Create hierarchical global outline with directory structure
        global_outline = self._build_hierarchical_outline(parsed_files, roles)

        # Calculate global statistics
        total_sections = sum(file_struct.section_count for file_struct in file_structures)
        max_depth = max((file_struct.outline.max_depth for file_struct in file_structures), default=0)

        return DocumentStructure(
            files=file_structures,
            global_outline=global_outline,
            total_files=len(file_structures),
            total_sections=total_sections,
            max_depth=max_depth,
        )

    def _adjust_section_levels(self, sections: List[Section], depth_adjustment: int) -> List[Section]:
        """
        Recursively adjust section levels by a given depth.

        Args:
            sections: List of sections to adjust
            depth_adjustment: Amount to add to each section level

        Returns:
            New list of sections with adjusted levels
        """
        adjusted_sections = []

        for section in sections:
            # Create a copy of the section with adjusted level
            adjusted_section = section.model_copy(deep=True)
            adjusted_section.level += depth_adjustment

            # Recursively adjust subsections
            if adjusted_section.subsections:
                adjusted_section.subsections = self._adjust_section_levels(
                    adjusted_section.subsections, depth_adjustment
                )

            adjusted_sections.append(adjusted_section)

        return adjusted_sections

    def _analyze_single_file(self, parsed_content: ParsedContent, heading_offset: int = 0) -> FileStructure:
        """Analyze structure of a single parsed file, bumping its headings by ``heading_offset``."""
        # Bump section levels so a file authored with plain #/## sits at the depth
        # implied by its chapter/sub-chapter nesting (Parts do not add a level).
        adjusted_sections = self._adjust_section_levels(parsed_content.sections, heading_offset)

        # Build TOC entries from adjusted sections
        toc_entries = self._build_toc_entries(adjusted_sections, parsed_content.source_file.path, parent_id=None)

        # Create file outline
        outline = DocumentOutline(
            entries=toc_entries,
            max_depth=self._calculate_max_depth(toc_entries),
            total_sections=len([e for e in self._flatten_entries(toc_entries)]),
        )

        # Extract title from frontmatter or first header
        title = parsed_content.frontmatter.title
        if not title and toc_entries:
            title = toc_entries[0].title

        # Calculate word count (rough estimate) using adjusted sections
        word_count = sum(len(section.content.split()) for section in adjusted_sections)

        # Create an updated ParsedContent with adjusted sections for downstream processing
        adjusted_parsed_content = parsed_content.model_copy(deep=True)
        adjusted_parsed_content.sections = adjusted_sections

        return FileStructure(
            file_path=parsed_content.source_file.path,
            relative_path=parsed_content.source_file.relative_path,
            parsed_content=adjusted_parsed_content,
            outline=outline,
            title=title,
            section_count=outline.total_sections,
            word_count=word_count,
        )

    def _build_toc_entries(
        self, sections: List[Section], source_file: Path, parent_id: Optional[str] = None
    ) -> List[TocEntry]:
        """Build TOC entries from section hierarchy."""
        entries = []

        for section in sections:
            # Generate section number
            section_number = self._generate_section_number(section.level)

            # Create TOC entry
            entry = TocEntry(
                level=section.level,
                title=section.title,
                id=section.id,
                number=section_number,
                source_file=source_file,
                line_number=section.line_start,
                parent_id=parent_id,
            )

            # Process subsections recursively
            if section.subsections:
                entry.children = self._build_toc_entries(section.subsections, source_file, parent_id=section.id)

            entries.append(entry)

        return entries

    def _build_unnumbered_toc_entries(
        self, sections: List[Section], source_file: Path, parent_id: Optional[str] = None
    ) -> List[TocEntry]:
        """Build TOC entries from sections without automatic numbering (for front matter)."""
        entries = []

        for section in sections:
            # Create TOC entry without numbering
            entry = TocEntry(
                level=section.level,
                title=section.title,
                id=section.id,
                number="",  # No automatic numbering
                source_file=source_file,
                line_number=section.line_start,
                parent_id=parent_id,
            )

            # Process subsections recursively
            if section.subsections:
                entry.children = self._build_unnumbered_toc_entries(
                    section.subsections, source_file, parent_id=section.id
                )

            entries.append(entry)

        return entries

    def _generate_section_number(self, level: int) -> str:
        """Generate section number based on numbering style."""
        if self.numbering_style == "none":
            return ""

        # Update counter for this level
        self.section_counters[level] = self.section_counters.get(level, 0) + 1

        # Reset counters for deeper levels
        levels_to_reset = [lvl for lvl in self.section_counters.keys() if lvl > level]
        for lvl in levels_to_reset:
            del self.section_counters[lvl]

        if self.numbering_style == "flat":
            # Simple incremental numbering
            total_sections = sum(self.section_counters.values())
            return str(total_sections)

        elif self.numbering_style == "hierarchical":
            # Hierarchical numbering (1.1.1)
            relevant_levels = sorted([lvl for lvl in self.section_counters.keys() if lvl <= level])
            number_parts = [str(self.section_counters[lvl]) for lvl in relevant_levels]
            return ".".join(number_parts)

        return ""

    def _calculate_max_depth(self, entries: List[TocEntry]) -> int:
        """Calculate maximum depth in TOC hierarchy."""
        if not entries:
            return 0

        max_depth = 0
        for entry in entries:
            depth = entry.level
            if entry.children:
                depth = max(depth, self._calculate_max_depth(entry.children))
            max_depth = max(max_depth, depth)

        return max_depth

    def _flatten_entries(self, entries: List[TocEntry]) -> List[TocEntry]:
        """Flatten nested TOC entries into a list."""
        result = []
        for entry in entries:
            result.append(entry)
            result.extend(self._flatten_entries(entry.children))
        return result

    def _to_roman_numeral(self, num: int) -> str:
        """Convert integer to roman numeral."""
        values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        numerals = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        result = ""
        for i, value in enumerate(values):
            count = num // value
            result += numerals[i] * count
            num -= value * count
        return result

    def _build_hierarchical_outline(self, parsed_files: List[ParsedContent], roles: Dict[str, Role]) -> DocumentOutline:
        """
        Build a nested outline from structural roles: Part > Chapter/Appendix >
        Sub-chapter > the sections written inside each file.

        Files are consumed in their already-sorted order, so each tier is created
        the first time a file enters it and reused afterwards.
        """
        if not self.project_root or not roles:
            return self._flat_outline(parsed_files)

        any_parts = any(role == Role.PART for role in roles.values())
        part_base = 1 if any_parts else 0

        top_entries: List[TocEntry] = []
        part_entries: Dict[str, TocEntry] = {}
        chapter_entries: Dict[str, TocEntry] = {}
        subchapter_entries: Dict[str, TocEntry] = {}
        chapter_counter = 0
        appendix_ord = ord("A") - 1
        front_matter_counter = 0

        for parsed_content in parsed_files:
            rel = _relative_posix(parsed_content, self.project_root)
            if rel is None:
                continue

            tiers = file_tiers(rel, roles)
            source = parsed_content.source_file.path

            # Front matter with no chapter: unnumbered entries with lowercase-roman numbers.
            if tiers.is_front_matter and not tiers.chapter_key:
                fm_entries = self._build_unnumbered_toc_entries(parsed_content.sections, source)
                for entry in fm_entries:
                    if entry.level <= 1:
                        front_matter_counter += 1
                        entry.number = self._to_roman_numeral(front_matter_counter).lower()
                top_entries.extend(fm_entries)
                continue

            container = top_entries

            if tiers.part_key:
                pentry = part_entries.get(tiers.part_key)
                if pentry is None:
                    pentry = TocEntry(
                        level=1,
                        title=tiers.part_title,
                        id=self._generate_id(f"part-{tiers.part_key}"),
                        number="",
                        source_file=source,
                        line_number=1,
                        children=[],
                    )
                    top_entries.append(pentry)
                    part_entries[tiers.part_key] = pentry
                container = pentry.children

            owner: Optional[TocEntry] = None

            if tiers.chapter_key:
                centry = chapter_entries.get(tiers.chapter_key)
                if centry is None:
                    if tiers.is_appendix:
                        appendix_ord += 1
                        number = chr(appendix_ord)
                    else:
                        chapter_counter += 1
                        number = str(chapter_counter)
                    centry = TocEntry(
                        level=part_base + 1,
                        title=tiers.chapter_title,
                        id=self._generate_id(f"chapter-{tiers.chapter_key}"),
                        number=number,
                        source_file=source,
                        line_number=1,
                        children=[],
                    )
                    centry.__dict__["_counters"] = {0: number}
                    container.append(centry)
                    chapter_entries[tiers.chapter_key] = centry
                container = centry.children
                owner = centry

            if tiers.subchapter_key:
                sentry = subchapter_entries.get(tiers.subchapter_key)
                if sentry is None:
                    # A sub-chapter continues its chapter's section sequence
                    # (…, 3.2 section, 3.3 sub-chapter), so numbers never collide.
                    chapter_counters = owner.__dict__["_counters"]
                    chapter_counters[1] = chapter_counters.get(1, 0) + 1
                    for deeper in [lvl for lvl in list(chapter_counters) if lvl > 1]:
                        del chapter_counters[deeper]
                    sub_number = f"{chapter_counters[0]}.{chapter_counters[1]}"
                    sentry = TocEntry(
                        level=part_base + 2,
                        title=tiers.subchapter_title,
                        id=self._generate_id(f"subchapter-{tiers.subchapter_key}"),
                        number=sub_number,
                        source_file=source,
                        line_number=1,
                        children=[],
                    )
                    sentry.__dict__["_counters"] = {0: sub_number}
                    container.append(sentry)
                    subchapter_entries[tiers.subchapter_key] = sentry
                container = sentry.children
                owner = sentry

            # Attach this file's own section headings under its deepest tier.
            if owner is not None:
                self.section_counters = owner.__dict__["_counters"]
                base = owner.level
            else:
                self._reset_counters()
                base = part_base

            file_entries = self._build_toc_entries(parsed_content.sections, source)
            self._shift_levels(file_entries, base)
            container.extend(file_entries)

        return DocumentOutline(
            entries=top_entries,
            max_depth=max((self._calculate_max_depth([entry]) for entry in top_entries), default=0),
            total_sections=len(self._flatten_entries(top_entries)),
        )

    def _flat_outline(self, parsed_files: List[ParsedContent]) -> DocumentOutline:
        """Fallback outline (no project root / no roles): each file's sections in order."""
        self._reset_counters()
        all_entries: List[TocEntry] = []
        for parsed_content in parsed_files:
            all_entries.extend(self._build_toc_entries(parsed_content.sections, parsed_content.source_file.path))

        return DocumentOutline(
            entries=all_entries,
            max_depth=max((self._calculate_max_depth([entry]) for entry in all_entries), default=0),
            total_sections=len(self._flatten_entries(all_entries)),
        )

    def _shift_levels(self, entries: List[TocEntry], delta: int) -> None:
        """Add ``delta`` to the level of every entry and its descendants, in place."""
        for entry in entries:
            entry.level += delta
            if entry.children:
                self._shift_levels(entry.children, delta)

    def _generate_id(self, title: str) -> str:
        """Generate HTML-safe ID from title."""
        import re

        # Convert to lowercase, replace spaces/punctuation with hyphens
        id_str = re.sub(r"[^\w\s-]", "", title.lower())
        id_str = re.sub(r"[\s_-]+", "-", id_str)
        return id_str.strip("-")

    def _reset_counters(self) -> None:
        """Reset section numbering counters."""
        self.section_counters.clear()


def build_document_structure(parsed_files: List[ParsedContent]) -> DocumentStructure:
    """
    Convenience function to build document structure from parsed files.

    Args:
        parsed_files: List of ParsedContent objects

    Returns:
        DocumentStructure: Complete hierarchical structure
    """
    analyzer = StructureAnalysis()
    return analyzer.analyze_files(parsed_files)

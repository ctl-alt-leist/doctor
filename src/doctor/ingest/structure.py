"""
Structure Analysis (H) → Document Structure (N)

Builds hierarchical document structure from parsed content:
- Table of contents generation
- Section numbering and hierarchy
- Document outline and navigation
- Cross-document structure relationships
"""

from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field, computed_field

from doctor.discovery import extract_roman_prefix
from doctor.ingest.content import ParsedContent, Section


class TocEntry(BaseModel):
    """Table of contents entry."""

    level: int  # 1=h1, 2=h2, etc.
    title: str  # "Mathematical Foundations"
    id: str  # "mathematical-foundations"
    number: str  # "2.1" or "2.1.3"
    page_number: Optional[int] = None  # For PDF generation

    # Source location
    source_file: Path
    line_number: int

    # Hierarchy
    parent_id: Optional[str] = None
    children: List["TocEntry"] = Field(default_factory=list)


class DocumentOutline(BaseModel):
    """Complete document outline with numbered sections."""

    entries: List[TocEntry] = Field(default_factory=list)
    max_depth: int = 0
    total_sections: int = 0

    @computed_field
    @property
    def flat_entries(self) -> List[TocEntry]:
        """Get all entries as a flat list in document order."""
        # Check if we have pre-computed flat entries (for global outline)
        if hasattr(self, "_flat_entries"):
            return self._flat_entries

        def flatten(entries: List[TocEntry]) -> List[TocEntry]:
            result = []
            for entry in entries:
                result.append(entry)
                result.extend(flatten(entry.children))
            return result

        return flatten(self.entries)

    def get_entry_by_id(self, section_id: str) -> Optional[TocEntry]:
        """Find TOC entry by section ID."""
        for entry in self.flat_entries:
            if entry.id == section_id:
                return entry
        return None

    def get_entries_by_level(self, level: int) -> List[TocEntry]:
        """Get all entries at a specific level."""
        return [entry for entry in self.flat_entries if entry.level == level]


class FileStructure(BaseModel):
    """Structure information for a single file."""

    file_path: Path
    relative_path: Path
    parsed_content: ParsedContent
    outline: DocumentOutline

    # File-level metadata
    title: Optional[str] = None
    section_count: int = 0
    word_count: int = 0

    # Chapter information for Roman numeral chapters
    chapter_title: Optional[str] = None  # Full chapter title (e.g., "III. Quantum Mechanics")
    is_first_in_chapter: bool = False  # True if this is the first file in a Roman numeral chapter

    @computed_field
    @property
    def display_name(self) -> str:
        """Get display name for this file."""
        if self.title:
            return self.title
        return self.parsed_content.source_file.stem


class DocumentStructure(BaseModel):
    """
    Complete document structure across all files.

    This is the main output of Structure Analysis (H).
    """

    files: List[FileStructure] = Field(default_factory=list)
    global_outline: DocumentOutline = Field(default_factory=DocumentOutline)

    # Global structure metadata
    total_files: int = 0
    total_sections: int = 0
    max_depth: int = 0

    def get_file_by_path(self, path: Path) -> Optional[FileStructure]:
        """Find file structure by path."""
        for file_struct in self.files:
            if file_struct.file_path == path or file_struct.relative_path == path:
                return file_struct
        return None

    def get_all_sections(self) -> List[TocEntry]:
        """Get all sections across all files."""
        return self.global_outline.flat_entries

    def get_navigation_structure(self) -> Dict[str, List[TocEntry]]:
        """Get navigation structure organized by file."""
        nav = {}
        for file_struct in self.files:
            nav[str(file_struct.relative_path)] = file_struct.outline.entries
        return nav


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
        all_toc_entries = []

        # Reset counters for global numbering
        self._reset_counters()

        # Track seen chapters for Roman numeral chapter detection
        seen_chapters: Set[str] = set()

        # Process each file
        for parsed_content in parsed_files:
            file_struct = self._analyze_single_file(parsed_content)

            # Detect Roman numeral chapters
            chapter_info = self._detect_chapter_info(parsed_content, seen_chapters)
            if chapter_info:
                file_struct.chapter_title = chapter_info["title"]
                file_struct.is_first_in_chapter = chapter_info["is_first"]

            file_structures.append(file_struct)
            all_toc_entries.extend(file_struct.outline.flat_entries)

        # Create hierarchical global outline with directory structure
        global_outline = self._build_hierarchical_outline(parsed_files)

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

    def _calculate_directory_depth(self, parsed_content: ParsedContent) -> int:
        """
        Calculate the directory depth for a file.

        Depth is the number of parent directories from the project root.
        For example:
        - Project/file.md -> depth = 0
        - Project/Part1/file.md -> depth = 1
        - Project/Part1/Chapter1/file.md -> depth = 2
        """
        if not self.project_root:
            return 0

        try:
            relative_path = parsed_content.source_file.path.relative_to(self.project_root)
            # Number of parent directories (not counting the file itself)
            parent_parts = relative_path.parent.parts
            return len(parent_parts)
        except ValueError:
            # File is not relative to project root
            return 0

    def _detect_chapter_info(
        self, parsed_content: ParsedContent, seen_chapters: Set[str]
    ) -> Optional[Dict[str, any]]:
        """
        Detect if a file belongs to a Roman numeral chapter.

        Args:
            parsed_content: The parsed content of the file
            seen_chapters: Set of chapter titles already seen (modified in place)

        Returns:
            Dict with 'title' and 'is_first' keys, or None if not a Roman numeral chapter
        """
        if not self.project_root:
            return None

        try:
            relative_path = parsed_content.source_file.path.relative_to(self.project_root)
            parent_parts = relative_path.parent.parts

            if not parent_parts:
                return None

            # Get the top-level directory
            top_level_dir = parent_parts[0]

            # Check if it's a Roman numeral chapter
            roman_prefix = extract_roman_prefix(top_level_dir)
            if roman_prefix is None:
                return None

            # This is a Roman numeral chapter
            chapter_title = top_level_dir
            is_first = chapter_title not in seen_chapters

            if is_first:
                seen_chapters.add(chapter_title)

            return {"title": chapter_title, "is_first": is_first}

        except ValueError:
            return None

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

    def _analyze_single_file(self, parsed_content: ParsedContent) -> FileStructure:
        """Analyze structure of a single parsed file."""
        # Calculate directory depth for hierarchical header adjustment
        dir_depth = self._calculate_directory_depth(parsed_content)

        # Adjust section levels based on directory depth
        adjusted_sections = self._adjust_section_levels(parsed_content.sections, dir_depth)

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

    def _build_global_outline(self, all_entries: List[TocEntry]) -> DocumentOutline:
        """Build global outline from all file entries."""
        # Create a custom outline that stores the flattened entries directly
        outline = DocumentOutline(
            entries=[],  # Don't use the hierarchical entries field
            max_depth=max((entry.level for entry in all_entries), default=0),
            total_sections=len(all_entries),
        )
        # Override the computed flat_entries by storing them directly
        outline.__dict__["_flat_entries"] = all_entries
        return outline

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

    def _build_hierarchical_outline(self, parsed_files: List[ParsedContent]) -> DocumentOutline:
        """Build hierarchical outline that recognizes directory structure."""
        from collections import defaultdict

        # Group files by directory
        dir_files = defaultdict(list)
        for parsed_content in parsed_files:
            # Extract directory name from path
            file_path = parsed_content.source_file.path
            parent = file_path.parent
            if parent.name and parent.name != ".":
                dir_name = parent.name
            else:
                dir_name = "Root"
            dir_files[dir_name].append(parsed_content)

        # Sort directories by natural ordering (0. Front Matter, 1. Chapter, etc.)
        sorted_dirs = sorted(dir_files.keys(), key=self._natural_sort_key)

        all_entries = []
        directory_level_counter = 0
        appendix_counter = 0

        for dir_name in sorted_dirs:
            files = dir_files[dir_name]

            # Determine if this is front matter (starts with "0." or contains "front")
            is_front_matter = (
                dir_name.lower().startswith("0.")
                or "front" in dir_name.lower()
                or dir_name.lower().startswith("i.")
                or dir_name.lower().startswith("ii.")
            )

            # Skip page numbering for front matter directories
            if not is_front_matter:
                # Handle appendices with letter numbering
                if (
                    dir_name.lower().startswith("a.")
                    or "appendix" in dir_name.lower()
                    or "appendices" in dir_name.lower()
                ):
                    dir_number = chr(ord("A") + appendix_counter)
                    appendix_counter += 1
                else:
                    directory_level_counter += 1
                    dir_number = str(directory_level_counter)
            else:
                dir_number = ""

            # Handle front matter specially - don't create directory entry
            if is_front_matter:
                # Add front matter files directly to TOC (no directory wrapper)
                front_matter_counter = 0
                for parsed_content in sorted(files, key=lambda f: self._natural_sort_key(f.source_file.name)):
                    file_entries = self._build_unnumbered_toc_entries(
                        parsed_content.sections, parsed_content.source_file.path, parent_id=None
                    )

                    # Apply roman numerals to front matter entries and keep at original levels
                    for entry in file_entries:
                        if entry.level <= 2:  # Top-level front matter entries (could be level 1 or 2)
                            front_matter_counter += 1
                            entry.number = self._to_roman_numeral(front_matter_counter).lower()
                    all_entries.extend(file_entries)
            else:
                # Create directory-level TOC entry for chapters
                dir_entry = TocEntry(
                    level=1,  # Chapter level
                    title=self._clean_directory_title(dir_name),
                    id=self._generate_id(dir_name),
                    number=dir_number,
                    source_file=files[0].source_file.path,  # Use first file as source
                    line_number=1,
                    children=[],
                )

                # Reset section counters for each new chapter/directory
                self._reset_counters()

                # For book format, show appropriate depth (levels 1-3)
                for parsed_content in sorted(files, key=lambda f: self._natural_sort_key(f.source_file.name)):
                    file_entries = self._build_toc_entries(
                        parsed_content.sections, parsed_content.source_file.path, parent_id=dir_entry.id
                    )

                    # Adjust levels for book TOC structure
                    def adjust_entry_levels(
                        entries, depth_limit=3, is_numbered_chapter=bool(dir_number), chapter_number=dir_number
                    ):
                        adjusted_entries = []
                        for entry in entries:
                            if entry.level <= depth_limit:  # Include levels 1-3
                                # Shift levels: file H1->chapter H2, file H2->chapter H3, etc.
                                entry.level += 1

                                # Update numbering for main chapters (not front matter)
                                if is_numbered_chapter:
                                    if entry.number:
                                        entry.number = f"{chapter_number}.{entry.number}"
                                    else:
                                        # Generate section number based on level
                                        entry.number = f"{chapter_number}.1"

                                # Recursively adjust children
                                entry.children = adjust_entry_levels(
                                    entry.children, depth_limit, is_numbered_chapter, chapter_number
                                )
                                adjusted_entries.append(entry)
                        return adjusted_entries

                    adjusted_entries = adjust_entry_levels(file_entries)
                    dir_entry.children.extend(adjusted_entries)

                all_entries.append(dir_entry)

        return DocumentOutline(
            entries=all_entries,
            max_depth=max((self._calculate_max_depth([entry]) for entry in all_entries), default=0),
            total_sections=len(self._flatten_entries(all_entries)),
        )

    def _clean_directory_title(self, dir_name: str) -> str:
        """Clean directory name for display in TOC."""
        # Remove numbering prefix (e.g., "1. " -> "")
        import re

        cleaned = re.sub(r"^\d+\.\s*", "", dir_name)
        cleaned = re.sub(r"^[ivx]+\.\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned if cleaned else dir_name

    def _generate_id(self, title: str) -> str:
        """Generate HTML-safe ID from title."""
        import re

        # Convert to lowercase, replace spaces/punctuation with hyphens
        id_str = re.sub(r"[^\w\s-]", "", title.lower())
        id_str = re.sub(r"[\s_-]+", "-", id_str)
        return id_str.strip("-")

    def _natural_sort_key(self, text: str) -> list:
        """Generate natural sorting key for alphanumeric text."""
        import re

        def convert(text_part):
            if text_part.isdigit():
                return int(text_part)
            return text_part.lower()

        return [convert(c) for c in re.split(r"(\d+)", text)]

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

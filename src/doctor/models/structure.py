"""
Document structure models.

These models represent the hierarchical structure of documents:
- Table of contents entries
- Document outlines
- File structure information
- Complete document structure across files
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, computed_field

from doctor.models.content import ParsedContent


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

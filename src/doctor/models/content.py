"""
Content data models for parsed document elements.

These models represent the parsed content extracted from markdown files:
- Frontmatter metadata
- Citations and links
- Sections and hierarchical structure

Math models are in doctor.models.math for future extensibility.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from doctor.discovery import MarkdownFile
from doctor.models.math import MathBlock


class FrontMatter(BaseModel):
    """YAML frontmatter from document header."""

    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    abstract: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Allow arbitrary fields for flexibility
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class Citation(BaseModel):
    """Citation reference [@key] or [@key1; @key2]."""

    keys: List[str]  # Bibliography keys
    line_number: int
    context: str  # Surrounding text for validation


class WikiLink(BaseModel):
    """Obsidian wikilink [[page]] or [[page|display]]."""

    target: str  # Target page/file
    display: Optional[str] = None  # Display text if different
    line_number: int


class FigureEmbed(BaseModel):
    """Figure embed ![[image.png]] or ![[image.png|caption]]."""

    path: str  # Image file path
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    line_number: int


class FootnoteRef(BaseModel):
    """Footnote reference [^1] or [^note-id]."""

    identifier: str  # "1", "note-id", etc.
    line_number: int
    position: int  # Character position in line


class FootnoteDef(BaseModel):
    """Footnote definition [^1]: Content here."""

    identifier: str  # "1", "note-id", etc.
    content: str  # The footnote text content
    line_number: int


class Section(BaseModel):
    """Document section with hierarchical structure."""

    level: int  # 1=h1, 2=h2, etc.
    title: str  # "Mathematical Foundations"
    id: str  # "mathematical-foundations"
    content: str  # Raw markdown content (without header)
    line_start: int
    line_end: int

    # Child sections
    subsections: List["Section"] = Field(default_factory=list)

    # Content elements within this section
    math_blocks: List[MathBlock] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    wiki_links: List[WikiLink] = Field(default_factory=list)
    figure_embeds: List[FigureEmbed] = Field(default_factory=list)
    footnote_refs: List[FootnoteRef] = Field(default_factory=list)
    footnote_defs: List[FootnoteDef] = Field(default_factory=list)


class ParsedContent(BaseModel):
    """Complete parsed document content."""

    source_file: MarkdownFile
    frontmatter: FrontMatter
    sections: List[Section] = Field(default_factory=list)

    # Global content elements
    all_math_blocks: List[MathBlock] = Field(default_factory=list)
    all_citations: List[Citation] = Field(default_factory=list)
    all_wiki_links: List[WikiLink] = Field(default_factory=list)
    all_figure_embeds: List[FigureEmbed] = Field(default_factory=list)
    all_footnote_refs: List[FootnoteRef] = Field(default_factory=list)
    all_footnote_defs: List[FootnoteDef] = Field(default_factory=list)

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, v: List[Section]) -> List[Section]:
        """Validate section hierarchy."""
        return v

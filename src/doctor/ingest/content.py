"""
Content Ingestion (G) → Parsed Content (L)

Parses markdown files into structured content with:
- YAML frontmatter extraction
- Section hierarchy from headers
- LaTeX math block identification
- Citation and link discovery
- Block-level content parsing
"""

import re
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator

from doctor.discovery import MarkdownFile


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


class MathBlock(BaseModel):
    """LaTeX math block ($$...$$ or $...$)."""

    content: str  # LaTeX source
    display: bool  # True for $$, False for $
    line_start: int
    line_end: int
    block_id: Optional[str] = None  # For referencing ^eq-id


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


class ContentIngestion:
    """
    Content Ingestion processor (G in architecture diagram).

    Converts raw markdown files into structured ParsedContent objects.
    """

    def __init__(self):
        # Regex patterns for content extraction
        self.frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL)
        self.header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        self.math_display_pattern = re.compile(r"\$\$(.*?)\$\$", re.DOTALL)
        self.math_inline_pattern = re.compile(r"(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)")
        self.citation_pattern = re.compile(r"\[@([^\]]+)\]")
        self.wikilink_pattern = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
        self.figure_pattern = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
        self.footnote_ref_pattern = re.compile(r"\[\^([^\]]+)\]")  # [^1] or [^note-id]
        self.footnote_def_pattern = re.compile(r"^\[\^([^\]]+)\]:\s*(.*?)(?=^\[\^|\Z)", re.MULTILINE | re.DOTALL)
        self.code_fence_pattern = re.compile(r"^(```|~~~)", re.MULTILINE)

    def ingest_file(self, md_file: MarkdownFile) -> ParsedContent:
        """
        Main ingestion method - parse a markdown file completely.

        Args:
            md_file: MarkdownFile object with loaded content

        Returns:
            ParsedContent: Structured document content
        """
        if not md_file.content:
            md_file.load_content()

        content = md_file.content

        # Extract frontmatter
        frontmatter, content_body = self._extract_frontmatter(content)

        # Parse sections and their content
        sections = self._parse_sections(content_body)

        # Extract all global elements
        all_math = self._extract_all_math_blocks(content_body)
        all_citations = self._extract_all_citations(content_body)
        all_wikilinks = self._extract_all_wikilinks(content_body)
        all_figures = self._extract_all_figures(content_body)
        all_footnote_refs, all_footnote_defs = self._extract_all_footnotes(content_body)

        return ParsedContent(
            source_file=md_file,
            frontmatter=frontmatter,
            sections=sections,
            all_math_blocks=all_math,
            all_citations=all_citations,
            all_wiki_links=all_wikilinks,
            all_figure_embeds=all_figures,
            all_footnote_refs=all_footnote_refs,
            all_footnote_defs=all_footnote_defs,
        )

    def _extract_frontmatter(self, content: str) -> Tuple[FrontMatter, str]:
        """Extract YAML frontmatter and return (metadata, remaining_content)."""
        match = self.frontmatter_pattern.match(content)

        if not match:
            return FrontMatter(), content

        yaml_content = match.group(1)
        remaining_content = content[match.end() :]

        try:
            yaml_data = yaml.safe_load(yaml_content) or {}

            # Separate known fields from extras
            known_fields = {"title", "author", "date", "abstract", "tags"}
            frontmatter_data = {}
            extra_data = {}

            for key, value in yaml_data.items():
                if key in known_fields:
                    frontmatter_data[key] = value
                else:
                    extra_data[key] = value

            frontmatter_data["extra"] = extra_data

            return FrontMatter(**frontmatter_data), remaining_content

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    def _parse_sections(self, content: str) -> List[Section]:
        """Parse content into hierarchical sections based on headers."""
        lines = content.split("\n")
        sections = []
        current_section = None
        current_content = []
        in_code_block = False
        code_block_type = None

        for line_num, line in enumerate(lines, 1):
            # Track code block boundaries
            stripped_line = line.strip()

            # Check for fenced code blocks (``` or ```)
            if stripped_line.startswith("```") or stripped_line.startswith("~~~"):
                if in_code_block and code_block_type == "fenced":
                    in_code_block = False
                    code_block_type = None
                elif not in_code_block:
                    in_code_block = True
                    code_block_type = "fenced"
                current_content.append(line)
                continue

            # Check for indented code blocks (4+ spaces or 1+ tab at start)
            if not in_code_block and (line.startswith("    ") or line.startswith("\t")):
                # This is an indented code block line
                current_content.append(line)
                continue

            # Only check for headers if we're NOT in a code block
            if not in_code_block:
                header_match = self.header_pattern.match(line)

                if header_match:
                    # Save previous section if exists
                    if current_section:
                        current_section.content = "\n".join(current_content).strip()
                        current_section.line_end = line_num - 1
                        sections.append(current_section)

                    # Start new section
                    level = len(header_match.group(1))  # Count #
                    title = header_match.group(2).strip()
                    section_id = self._generate_section_id(title)

                    current_section = Section(
                        level=level, title=title, id=section_id, content="", line_start=line_num, line_end=line_num
                    )
                    current_content = []
                    continue

            # Add to current section content (both regular lines and code block lines)
            current_content.append(line)

        # Handle final section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            current_section.line_end = len(lines)
            sections.append(current_section)

        # Build hierarchical structure
        return self._build_section_hierarchy(sections)

    def _generate_section_id(self, title: str) -> str:
        """Generate URL-safe section ID from title."""
        # Convert to lowercase, replace spaces/special chars with hyphens
        section_id = re.sub(r"[^\w\s-]", "", title.lower())
        section_id = re.sub(r"[\s_-]+", "-", section_id)
        return section_id.strip("-")

    def _get_code_block_regions(self, content: str) -> List[Tuple[int, int]]:
        """
        Identify code block regions in content.

        Returns list of (start_pos, end_pos) tuples for each code block.
        """
        regions = []
        lines = content.split("\n")
        in_code_block = False
        code_start = 0
        current_pos = 0

        for line_num, line in enumerate(lines):
            stripped = line.strip()

            # Check for fenced code blocks
            if stripped.startswith("```") or stripped.startswith("~~~"):
                if in_code_block:
                    # End of code block
                    regions.append((code_start, current_pos + len(line)))
                    in_code_block = False
                else:
                    # Start of code block
                    code_start = current_pos
                    in_code_block = True

            current_pos += len(line) + 1  # +1 for newline

        # Handle unclosed code block
        if in_code_block:
            regions.append((code_start, len(content)))

        return regions

    def _is_in_code_block(self, position: int, code_regions: List[Tuple[int, int]]) -> bool:
        """Check if a position is inside a code block."""
        for start, end in code_regions:
            if start <= position < end:
                return True
        return False

    def _build_section_hierarchy(self, flat_sections: List[Section]) -> List[Section]:
        """Build hierarchical section structure from flat list."""
        if not flat_sections:
            return []

        root_sections = []
        section_stack = []

        for section in flat_sections:
            # Pop sections from stack until we find appropriate parent
            while section_stack and section_stack[-1].level >= section.level:
                section_stack.pop()

            if section_stack:
                # Add as subsection to parent
                section_stack[-1].subsections.append(section)
            else:
                # Add as root section
                root_sections.append(section)

            section_stack.append(section)

        return root_sections

    def _extract_all_math_blocks(self, content: str) -> List[MathBlock]:
        """Extract all LaTeX math blocks from content."""
        math_blocks = []
        lines = content.split("\n")
        code_regions = self._get_code_block_regions(content)

        # Display math ($$...$)
        for match in self.math_display_pattern.finditer(content):
            # Skip if inside code block
            if self._is_in_code_block(match.start(), code_regions):
                continue

            line_start = content[: match.start()].count("\n") + 1
            line_end = content[: match.end()].count("\n") + 1

            math_blocks.append(
                MathBlock(content=match.group(1).strip(), display=True, line_start=line_start, line_end=line_end)
            )

        # Inline math ($...$) - simple extraction
        current_pos = 0
        for line_num, line in enumerate(lines, 1):
            for match in self.math_inline_pattern.finditer(line):
                # Calculate absolute position in content
                abs_pos = current_pos + match.start()

                # Skip if inside code block
                if not self._is_in_code_block(abs_pos, code_regions):
                    math_blocks.append(
                        MathBlock(content=match.group(1).strip(), display=False, line_start=line_num, line_end=line_num)
                    )
            current_pos += len(line) + 1  # +1 for newline

        return math_blocks

    def _extract_all_citations(self, content: str) -> List[Citation]:
        """Extract all citation references [@key] from content."""
        citations = []
        lines = content.split("\n")
        code_regions = self._get_code_block_regions(content)

        current_pos = 0
        for line_num, line in enumerate(lines, 1):
            for match in self.citation_pattern.finditer(line):
                # Calculate absolute position in content
                abs_pos = current_pos + match.start()

                # Skip if inside code block
                if not self._is_in_code_block(abs_pos, code_regions):
                    keys = [k.strip().lstrip("@") for k in match.group(1).split(";")]
                    citations.append(Citation(keys=keys, line_number=line_num, context=line.strip()))

            current_pos += len(line) + 1  # +1 for newline

        return citations

    def _extract_all_wikilinks(self, content: str) -> List[WikiLink]:
        """Extract all wikilinks [[page]] from content."""
        wikilinks = []
        lines = content.split("\n")
        code_regions = self._get_code_block_regions(content)

        current_pos = 0
        for line_num, line in enumerate(lines, 1):
            for match in self.wikilink_pattern.finditer(line):
                # Calculate absolute position in content
                abs_pos = current_pos + match.start()

                # Skip if inside code block
                if not self._is_in_code_block(abs_pos, code_regions):
                    target = match.group(1).strip()
                    display = match.group(2).strip() if match.group(2) else None
                    wikilinks.append(WikiLink(target=target, display=display, line_number=line_num))

            current_pos += len(line) + 1  # +1 for newline

        return wikilinks

    def _extract_all_figures(self, content: str) -> List[FigureEmbed]:
        """Extract all figure embeds ![[image]] from content."""
        figures = []
        lines = content.split("\n")
        code_regions = self._get_code_block_regions(content)

        current_pos = 0
        for line_num, line in enumerate(lines, 1):
            for match in self.figure_pattern.finditer(line):
                # Calculate absolute position in content
                abs_pos = current_pos + match.start()

                # Skip if inside code block
                if not self._is_in_code_block(abs_pos, code_regions):
                    path = match.group(1).strip()
                    caption = match.group(2).strip() if match.group(2) else None
                    figures.append(FigureEmbed(path=path, caption=caption, line_number=line_num))

            current_pos += len(line) + 1  # +1 for newline

        return figures

    def _extract_all_footnotes(self, content: str) -> Tuple[List[FootnoteRef], List[FootnoteDef]]:
        """Extract all footnote references and definitions from content."""
        footnote_refs = []
        footnote_defs = []
        lines = content.split("\n")
        code_regions = self._get_code_block_regions(content)

        # Extract footnote references [^id]
        current_pos = 0
        for line_num, line in enumerate(lines, 1):
            for match in self.footnote_ref_pattern.finditer(line):
                # Calculate absolute position in content
                abs_pos = current_pos + match.start()

                # Skip if inside code block
                if not self._is_in_code_block(abs_pos, code_regions):
                    identifier = match.group(1).strip()
                    position = match.start()
                    footnote_refs.append(FootnoteRef(identifier=identifier, line_number=line_num, position=position))

            current_pos += len(line) + 1  # +1 for newline

        # Extract footnote definitions [^id]: Content
        # Use the full content for multiline footnote definitions
        for match in self.footnote_def_pattern.finditer(content):
            # Skip if inside code block
            if self._is_in_code_block(match.start(), code_regions):
                continue

            identifier = match.group(1).strip()
            footnote_content = match.group(2).strip()

            # Find line number where this definition starts
            line_num = content[: match.start()].count("\n") + 1

            footnote_defs.append(FootnoteDef(identifier=identifier, content=footnote_content, line_number=line_num))

        return footnote_refs, footnote_defs

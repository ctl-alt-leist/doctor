"""
Configuration models using Pydantic
Defines the structure of all configuration settings
"""

from enum import Enum
from typing import Dict, List, Union

from pydantic import BaseModel, Field


# Enums for configuration choices
class DocumentType(str, Enum):
    ARTICLE = "article"
    BOOK = "book"
    THESIS = "thesis"
    REPORT = "report"
    CUSTOM = "custom"


class PaperSize(str, Enum):
    A0 = "a0"
    A1 = "a1"
    A2 = "a2"
    A3 = "a3"
    A4 = "a4"
    A5 = "a5"
    A6 = "a6"
    A7 = "a7"
    A8 = "a8"
    A9 = "a9"
    A10 = "a10"
    LETTER = "letter"
    LEGAL = "legal"
    CUSTOM = "custom"


# Standard paper size dimensions (width x height) in centimeters
PAPER_DIMENSIONS = {
    "a0": ("84.1cm", "118.9cm"),
    "a1": ("59.4cm", "84.1cm"),
    "a2": ("42.0cm", "59.4cm"),
    "a3": ("29.7cm", "42.0cm"),
    "a4": ("21.0cm", "29.7cm"),
    "a5": ("14.8cm", "21.0cm"),
    "a6": ("10.5cm", "14.8cm"),
    "a7": ("7.4cm", "10.5cm"),
    "a8": ("5.2cm", "7.4cm"),
    "a9": ("3.7cm", "5.2cm"),
    "a10": ("2.6cm", "3.7cm"),
    "letter": ("21.6cm", "27.9cm"),
    "legal": ("21.6cm", "35.6cm"),
}


class CitationStyle(str, Enum):
    NATURE = "nature"
    SCIENCE = "science"
    APA = "apa"
    CHICAGO = "chicago"
    IEEE = "ieee"
    MLA = "mla"
    NUMERIC = "numeric"
    ALPHABETIC = "alphabetic"


class MathRenderer(str, Enum):
    MATHJAX = "mathjax"
    KATEX = "katex"


class OutputFormat(str, Enum):
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"


# Document Configuration
class DocumentLanguage(BaseModel):
    primary: str = "en"
    locale: str = "en-US"
    hyphenation: bool = True


class DocumentStructure(BaseModel):
    numbering_depth: int = Field(3, ge=0, le=6)
    toc_depth: int = Field(3, ge=0, le=6)
    include_toc: bool = True
    include_lot: bool = False  # List of tables
    include_lof: bool = False  # List of figures
    page_numbering: str = "arabic"
    section_style: str = "default"


class DocumentChapters(BaseModel):
    enabled: bool = False
    numbering: str = "arabic"
    include_in_toc: bool = True
    start_new_page: bool = True


class DocumentConfig(BaseModel):
    type: DocumentType = DocumentType.ARTICLE
    css_classes: Dict[str, str] = {
        "article": "document-type-article",
        "book": "document-type-book",
        "thesis": "document-type-thesis",
        "report": "document-type-report",
    }

    # Metadata
    title: str = ""
    subtitle: str = ""
    authors: List[str] = []
    affiliations: List[str] = []
    date: str = "auto"
    abstract: str = ""
    keywords: List[str] = []

    # Structure
    structure: DocumentStructure = DocumentStructure()
    language: DocumentLanguage = DocumentLanguage()
    chapters: DocumentChapters = DocumentChapters()


# Typography Configuration
class TypographyFonts(BaseModel):
    serif: List[str] = ["Crimson Text", "Source Serif Pro", "Charter", "Georgia", "serif"]
    sans: List[str] = ["Source Sans Pro", "Inter", "Helvetica Neue", "Arial", "sans-serif"]
    mono: List[str] = ["Fira Code", "Source Code Pro", "Consolas", "Monaco", "monospace"]


class TypographyWebFonts(BaseModel):
    google_fonts: List[str] = [
        "Crimson+Text:ital,wght@0,400;0,600;1,400;1,600",
        "Source+Sans+Pro:ital,wght@0,400;0,600;0,700;1,400;1,600",
        "Fira+Code:wght@400;500",
    ]


class TypographySizes(BaseModel):
    tiny: str = "0.6rem"
    scriptsize: str = "0.7rem"
    footnotesize: str = "0.8rem"
    small: str = "0.9rem"
    normal: str = "1rem"
    large: str = "1.2rem"
    Large: str = "1.4rem"
    LARGE: str = "1.7rem"
    huge: str = "2rem"
    Huge: str = "2.5rem"


class HeadingsConfig(BaseModel):
    """Heading typography configuration."""

    chapter_size: str = "2rem"
    section_size: str = "1.5rem"
    subsection_size: str = "1.2rem"
    subsubsection_size: str = "1.05rem"
    heading_color: str = "#1a3a5c"
    heading_weight: str = "600"
    heading_font: str = "sans"

    model_config = {"extra": "allow"}


class TypographyConfig(BaseModel):
    base_size: str = "16px"
    scale_ratio: float = Field(1.2, gt=1.0, le=2.0)
    line_height: float = Field(1.15, gt=0.8, le=3.0)
    paragraph_spacing: str = "0.5rem"
    paragraph_indent: str = "1.5rem"

    fonts: TypographyFonts = TypographyFonts()
    web_fonts: TypographyWebFonts = TypographyWebFonts()
    sizes: TypographySizes = TypographySizes()
    headings: HeadingsConfig = HeadingsConfig()


# Layout Configuration
class LayoutMargins(BaseModel):
    top: str = "2.5cm"
    bottom: str = "2.5cm"
    left: str = "2.5cm"
    right: str = "2.5cm"
    inner: str = "3cm"  # For two-sided documents
    outer: str = "2.5cm"  # For two-sided documents
    binding_offset: str = "0.5cm"


class LayoutSpacing(BaseModel):
    section_spacing: str = "2rem"
    paragraph_spacing: str = "0.5rem"
    list_spacing: str = "0.75rem"
    element_margin: str = "1rem"
    figure_margin: str = "2rem"
    table_margin: str = "2rem"


class LayoutWeb(BaseModel):
    max_width: str = "800px"
    responsive: bool = True
    mobile_breakpoint: str = "768px"
    tablet_breakpoint: str = "1024px"
    sidebar_width: str = "250px"
    content_padding: str = "2rem"


class LayoutConfig(BaseModel):
    paper_size: PaperSize = PaperSize.A4
    orientation: str = "portrait"
    custom_width: str = "21cm"
    custom_height: str = "29.7cm"

    columns: int = Field(1, ge=1, le=3)
    column_gap: str = "1.5rem"
    column_rule: bool = False

    margins: LayoutMargins = LayoutMargins()
    spacing: LayoutSpacing = LayoutSpacing()
    web: LayoutWeb = LayoutWeb()

    def get_paper_dimensions(self) -> tuple[str, str]:
        """Get paper dimensions (width, height) for the configured paper size."""
        if self.paper_size == PaperSize.CUSTOM:
            return (self.custom_width, self.custom_height)

        dimensions = PAPER_DIMENSIONS.get(self.paper_size.value)
        if not dimensions:
            # Fallback to A4 if size not found
            return PAPER_DIMENSIONS["a4"]

        if self.orientation == "landscape":
            # Swap width and height for landscape
            return (dimensions[1], dimensions[0])
        return dimensions

    def get_css_page_size(self) -> str:
        """Get CSS @page size value."""
        if self.paper_size == PaperSize.CUSTOM:
            width, height = self.get_paper_dimensions()
            return f"{width} {height}"
        else:
            return self.paper_size.value.upper()

    def get_playwright_format(self) -> str:
        """Get Playwright PDF format string."""
        if self.paper_size == PaperSize.CUSTOM:
            return "A4"  # Playwright doesn't support custom sizes directly
        else:
            return self.paper_size.value.upper()


# Math Configuration
class MathLatexPackages(BaseModel):
    amsmath: bool = True
    amssymb: bool = True
    amsfonts: bool = True
    amsthm: bool = True
    mathtools: bool = True
    physics: bool = True
    siunitx: bool = True
    upgreek: bool = True
    braket: bool = True


class MathStyling(BaseModel):
    bold_vectors: bool = True
    italic_variables: bool = True
    upright_operators: bool = True
    upright_differentials: bool = True


class MathHtmlConfig(BaseModel):
    mathjax_version: str = "3"
    mathjax_extensions: List[str] = ["tex-ams", "tex-physics", "tex-cancel"]
    katex_version: str = "latest"
    inline_delimiters: List[str] = ["$...$"]
    display_delimiters: List[str] = ["$$...$$"]


class MathConfig(BaseModel):
    renderer: MathRenderer = MathRenderer.MATHJAX
    equation_numbering: bool = True
    number_by_section: bool = False
    equation_prefix: str = ""
    center_equations: bool = True
    equation_spacing: str = "1rem"

    latex_packages: MathLatexPackages = MathLatexPackages()
    styling: MathStyling = MathStyling()
    html_config: MathHtmlConfig = MathHtmlConfig()


# Bibliography Configuration
class BibliographyCitations(BaseModel):
    cite_style: str = "numeric"
    brackets: str = "square"
    separator: str = ","
    sort_citations: bool = True
    compress_citations: bool = True
    max_authors_inline: int = 2


class BibliographyFormatting(BaseModel):
    hanging_indent: str = "1.5rem"
    entry_spacing: str = "0.5rem"
    font_size: str = "small"
    show_dois: bool = True
    show_urls: bool = False


class BibliographyHtml(BaseModel):
    link_citations: bool = True
    show_citation_preview: bool = True
    preview_max_length: int = 200


class BibliographyConfig(BaseModel):
    backend: str = "doctor"
    style: CitationStyle = CitationStyle.NATURE
    references_file: Union[str, List[str]] = "references.toml"
    title: str = "References"
    heading_level: int = 1

    citations: BibliographyCitations = BibliographyCitations()
    formatting: BibliographyFormatting = BibliographyFormatting()
    html: BibliographyHtml = BibliographyHtml()


# Figures Configuration
class FiguresSpacing(BaseModel):
    margin_top: str = "1.5rem"
    margin_bottom: str = "1.5rem"
    caption_spacing: str = "0.75rem"


class FiguresProcessing(BaseModel):
    supported_formats: List[str] = ["png", "jpg", "jpeg", "svg", "webp"]
    optimize_images: bool = True
    max_width_px: int = 1200


class FiguresCaptions(BaseModel):
    position: str = "bottom"
    format: str = "Figure {number}: "
    separator: str = ": "
    font_size: str = "small"
    alignment: str = "justified"
    width: str = "90%"


class TablesConfig(BaseModel):
    alignment: str = "center"
    column_spacing: str = "1rem"
    row_spacing: str = "0.5rem"
    border_width: str = "1px"
    style: str = "booktabs"


class FiguresConfig(BaseModel):
    default_width: str = "80%"
    max_width: str = "100%"
    default_height: str = "auto"
    alignment: str = "center"

    spacing: FiguresSpacing = FiguresSpacing()
    processing: FiguresProcessing = FiguresProcessing()
    captions: FiguresCaptions = FiguresCaptions()
    tables: TablesConfig = TablesConfig()


# Output Configuration
class OutputPdfMath(BaseModel):
    renderer: MathRenderer = MathRenderer.MATHJAX
    svg_output: bool = True
    dpi: int = 300


class OutputPdfMetadata(BaseModel):
    show_bookmarks: bool = True
    colorlinks: bool = True
    linkcolor: str = "#2980b9"
    citecolor: str = "#2980b9"
    urlcolor: str = "#2980b9"


class OutputPdf(BaseModel):
    engine: str = "weasyprint"  # weasyprint, playwright, puppeteer
    format: str = "A4"
    margins: str = "2.5cm"
    embed_fonts: bool = True
    compress: bool = True
    math: OutputPdfMath = OutputPdfMath()
    metadata: OutputPdfMetadata = OutputPdfMetadata()


class OutputHtml(BaseModel):
    html_version: str = "html5"
    html_mode: str = "single"  # "single" or "multi-page"
    standalone: bool = True
    include_toc: bool = True
    toc_depth: int = 3
    css_framework: str = "custom"
    include_css: bool = True
    mathjax_enabled: bool = True
    responsive_design: bool = True


class OutputConfig(BaseModel):
    output_dir: str = "output"
    filename_template: str = "{title}"
    sanitize_filenames: bool = True
    timestamp_suffix: bool = False
    formats: List[OutputFormat] = [OutputFormat.HTML, OutputFormat.PDF]

    pdf: OutputPdf = OutputPdf()
    html: OutputHtml = OutputHtml()


class StylingConfig(BaseModel):
    """Document styling and color configuration."""

    primary_color: str = "#1a3a5c"
    secondary_color: str = "#2c5282"
    accent_color: str = "#4a7298"
    text_color: str = "#1a1a1a"
    code_background: str = "#f6f8fa"
    code_border: str = "#e1e6eb"
    figure_border: str = "1px solid #dce3ea"
    figure_padding: str = "0.8rem"
    caption_color: str = "#4a5568"

    model_config = {"extra": "allow"}


# Main Configuration Model
class Config(BaseModel):
    """Main configuration model containing all settings."""

    document: DocumentConfig = DocumentConfig()
    typography: TypographyConfig = TypographyConfig()
    layout: LayoutConfig = LayoutConfig()
    math: MathConfig = MathConfig()
    bibliography: BibliographyConfig = BibliographyConfig()
    figures: FiguresConfig = FiguresConfig()
    output: OutputConfig = OutputConfig()
    styling: StylingConfig = StylingConfig()

    model_config = {
        # Allow extra fields for future extensibility
        "extra": "allow",
        # Use enum values instead of names
        "use_enum_values": True,
    }

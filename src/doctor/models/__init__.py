"""
Doctor data models package.

This package contains all the data models used throughout the doctor pipeline:
- Content models: Parsed document elements (sections, math, citations, etc.)
- Structure models: Document structure and hierarchy (TOC, outlines)
- Reference models: Cross-references and asset dependencies
- Bibliography models: Citations and bibliography entries
- Assembly models: Final assembled document for rendering
"""

from doctor.models.assembly import (
    AssembledDocument,
    FootnoteDefinition,
    FootnoteReference,
)
from doctor.models.bibliography import (
    BibliographyEntry,
    CitationDatabase,
    ProcessedCitation,
)
from doctor.models.content import (
    Citation,
    FigureEmbed,
    FootnoteDef,
    FootnoteRef,
    FrontMatter,
    ParsedContent,
    Section,
    WikiLink,
)
from doctor.models.math import MathBlock
from doctor.models.references import (
    AssetReference,
    ReferenceMap,
    ResolvedReference,
)
from doctor.models.structure import (
    DocumentOutline,
    DocumentStructure,
    FileStructure,
    TocEntry,
)


__all__ = [
    # Content models
    "FrontMatter",
    "MathBlock",
    "Citation",
    "WikiLink",
    "FigureEmbed",
    "FootnoteRef",
    "FootnoteDef",
    "Section",
    "ParsedContent",
    # Structure models
    "TocEntry",
    "DocumentOutline",
    "FileStructure",
    "DocumentStructure",
    # Reference models
    "ResolvedReference",
    "AssetReference",
    "ReferenceMap",
    # Bibliography models
    "BibliographyEntry",
    "ProcessedCitation",
    "CitationDatabase",
    # Assembly models
    "FootnoteReference",
    "FootnoteDefinition",
    "AssembledDocument",
]

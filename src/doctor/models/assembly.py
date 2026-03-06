"""
Assembled document data models.

These models represent the final assembled document ready for rendering:
- Footnote references and definitions
- Complete assembled document with all components
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from doctor.models.bibliography import CitationDatabase, ProcessedCitation
from doctor.models.references import ReferenceMap, ResolvedReference
from doctor.models.structure import DocumentStructure, TocEntry


@dataclass
class FootnoteReference:
    """A footnote reference found in the document text."""

    identifier: str  # Original identifier like "1", "note1", etc.
    number: int  # Sequential number for display (1, 2, 3...)
    position: int  # Character position in text
    file_path: str  # Source file containing the reference


@dataclass
class FootnoteDefinition:
    """A footnote definition/content."""

    identifier: str  # Original identifier matching the reference
    number: int  # Sequential number for display
    content: str  # The footnote text content
    file_path: str  # Source file containing the definition


class AssembledDocument(BaseModel):
    """
    Complete assembled document ready for template rendering.

    This is the final output of the ingestion pipeline.
    """

    # Core components
    document_structure: DocumentStructure
    reference_map: ReferenceMap
    citation_database: CitationDatabase

    # Assembled metadata
    title: str
    author: Optional[str] = None
    date: Optional[str] = None
    abstract: Optional[str] = None

    # Navigation and structure
    table_of_contents: List[TocEntry] = Field(default_factory=list)
    bibliography: List[Dict] = Field(default_factory=list)

    # Footnotes
    footnote_references: List[FootnoteReference] = Field(default_factory=list)
    footnote_definitions: List[FootnoteDefinition] = Field(default_factory=list)

    # Validation results
    total_files: int = 0
    total_sections: int = 0
    total_references: int = 0
    total_citations: int = 0
    total_footnotes: int = 0

    # Issues found during assembly
    broken_references: List[ResolvedReference] = Field(default_factory=list)
    missing_citations: List[ProcessedCitation] = Field(default_factory=list)
    orphaned_footnotes: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if document is valid for rendering."""
        return len(self.broken_references) == 0 and len(self.missing_citations) == 0

    @property
    def validation_summary(self) -> Dict[str, int]:
        """Get validation summary statistics."""
        return {
            "total_files": self.total_files,
            "total_sections": self.total_sections,
            "total_references": self.total_references,
            "total_citations": self.total_citations,
            "total_footnotes": self.total_footnotes,
            "broken_references": len(self.broken_references),
            "missing_citations": len(self.missing_citations),
            "orphaned_footnotes": len(self.orphaned_footnotes),
            "warnings": len(self.validation_warnings),
        }

"""
Bibliography and citation data models.

These models represent bibliography entries and processed citations:
- Bibliography entries from references.toml
- Processed citations with resolved references
- Citation database for the complete document
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BibliographyEntry(BaseModel):
    """Single bibliography entry from references.toml."""

    key: str  # Citation key like "weinberg-1995-a"

    # Standard bibliographic fields
    title: str
    author: str
    year: int

    # Entry type and specific fields - accept both 'type' and 'entry_type'
    entry_type: Optional[str] = None  # "article", "book", "inproceedings", etc.

    # Optional fields - accept both string and int for volume/number
    journal: Optional[str] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    isbn: Optional[str] = None
    arxiv: Optional[str] = None

    # Additional metadata
    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

    # Allow arbitrary additional fields
    extra_fields: Dict[str, Any] = Field(default_factory=dict)


class ProcessedCitation(BaseModel):
    """Processed citation with resolved bibliography information."""

    # Original citation info
    source_file: Path
    line_number: int
    original_keys: List[str]
    context: str

    # Resolved bibliography entries
    entries: List[BibliographyEntry] = Field(default_factory=list)
    missing_keys: List[str] = Field(default_factory=list)

    # Citation formatting
    citation_number: Optional[int] = None
    formatted_citation: Optional[str] = None
    is_valid: bool = False


class CitationDatabase(BaseModel):
    """
    Complete citation and bibliography database.

    This is the main output of Bibliography Processing (J).
    """

    # Bibliography entries indexed by key
    entries: Dict[str, BibliographyEntry] = Field(default_factory=dict)

    # Processed citations from documents
    citations: List[ProcessedCitation] = Field(default_factory=list)

    # Citation ordering for bibliography
    citation_order: List[str] = Field(default_factory=list)  # Keys in order of first appearance

    # Statistics
    # TODO: Should these be property methods?
    total_entries: int = 0
    total_citations: int = 0
    missing_citations: int = 0

    def get_entry(self, key: str) -> Optional[BibliographyEntry]:
        """Get bibliography entry by key."""
        return self.entries.get(key)

    def get_citations_for_file(self, file_path: Path) -> List[ProcessedCitation]:
        """Get all citations from a specific file."""
        return [cit for cit in self.citations if cit.source_file == file_path]

    def get_missing_citations(self) -> List[ProcessedCitation]:
        """Get citations with missing bibliography entries."""
        return [cit for cit in self.citations if not cit.is_valid]

    def get_ordered_bibliography(self) -> List[BibliographyEntry]:
        """Get bibliography entries in citation order."""
        return [self.entries[key] for key in self.citation_order if key in self.entries]

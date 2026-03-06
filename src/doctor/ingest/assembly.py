"""
Document Assembly (K)

Final assembly stage that combines all processed components:
- Parsed Content (L)
- Document Structure (N)
- Reference Map (O)
- Citation Database (P)

Creates a complete, ready-to-render document with all cross-references resolved.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from doctor.configs.models import Config
from doctor.ingest.bibliography import CitationDatabase, ProcessedCitation
from doctor.ingest.references import ReferenceMap, ResolvedReference
from doctor.ingest.structure import DocumentStructure, TocEntry


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
    bibliography: List[Dict] = Field(default_factory=list)  # Formatted bibliography entries

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
    orphaned_footnotes: List[str] = Field(default_factory=list)  # Footnotes without references/definitions
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


class DocumentAssembly:
    """
    Document Assembly processor (K in architecture diagram).

    Combines all processed components into final AssembledDocument.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.warnings: List[str] = []

    def assemble_document(
        self, document_structure: DocumentStructure, reference_map: ReferenceMap, citation_database: CitationDatabase
    ) -> AssembledDocument:
        """
        Assemble complete document from all processed components.

        Args:
            document_structure: Hierarchical document structure
            reference_map: Resolved cross-references
            citation_database: Bibliography and citations

        Returns:
            AssembledDocument: Complete assembled document
        """
        self.warnings.clear()

        # Extract document metadata
        title, author, date, abstract = self._extract_document_metadata(document_structure)

        # Build table of contents
        toc = self._build_table_of_contents(document_structure)

        # Format bibliography
        bibliography = self._format_bibliography(citation_database)

        # Process footnotes
        footnote_refs, footnote_defs, orphaned_footnotes = self._process_footnotes(document_structure)

        # Validate document integrity
        broken_refs = reference_map.get_broken_references()
        missing_citations = citation_database.get_missing_citations()

        # Perform additional validation
        self._validate_document_integrity(document_structure, reference_map, citation_database)

        return AssembledDocument(
            document_structure=document_structure,
            reference_map=reference_map,
            citation_database=citation_database,
            title=title,
            author=author,
            date=date,
            abstract=abstract,
            table_of_contents=toc,
            bibliography=bibliography,
            footnote_references=footnote_refs,
            footnote_definitions=footnote_defs,
            total_files=document_structure.total_files,
            total_sections=document_structure.total_sections,
            total_references=reference_map.total_references,
            total_citations=citation_database.total_citations,
            total_footnotes=len(footnote_refs),
            broken_references=broken_refs,
            missing_citations=missing_citations,
            orphaned_footnotes=orphaned_footnotes,
            validation_warnings=self.warnings.copy(),
        )

    def _extract_document_metadata(
        self, document_structure: DocumentStructure
    ) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Extract global document metadata from config first, then first file as fallback."""
        # Start with config values if available
        title = "Untitled Document"
        author = None
        date = None
        abstract = None

        if self.config and self.config.document:
            title = self.config.document.title or title
            # Convert authors list to string
            if self.config.document.authors:
                author = ", ".join(self.config.document.authors)
            date = self.config.document.date if self.config.document.date != "auto" else None
            abstract = self.config.document.abstract or None

        # Fall back to first file metadata if config values are empty
        if document_structure.files:
            first_file = document_structure.files[0]
            frontmatter = first_file.parsed_content.frontmatter

            if not title or title == "Untitled Document":
                title = frontmatter.title or first_file.display_name or title
            if not author:
                author = frontmatter.author
            if not date:
                date = frontmatter.date
            if not abstract:
                abstract = frontmatter.abstract

        # TODO: Could aggregate from multiple files or use specific title page

        return title, author, date, abstract

    def _build_table_of_contents(self, document_structure: DocumentStructure) -> List[TocEntry]:
        """Build complete table of contents, respecting configuration settings."""
        # Check if TOC should be included at all
        if self.config and self.config.document and self.config.document.structure:
            if not self.config.document.structure.include_toc:
                return []

        # Get all entries from global outline
        all_entries = document_structure.global_outline.flat_entries

        # Apply depth limit if configured
        if self.config and self.config.document and self.config.document.structure:
            toc_depth = self.config.document.structure.toc_depth
            # Filter entries to only include those at or below the specified depth
            filtered_entries = [entry for entry in all_entries if entry.level <= toc_depth]
            return filtered_entries

        return all_entries

    def _format_bibliography(self, citation_database: CitationDatabase) -> List[Dict]:
        """Format bibliography entries for rendering."""
        formatted_bib = []

        for entry in citation_database.get_ordered_bibliography():
            # Basic formatting - could be enhanced with proper citation styles
            formatted_entry = {
                "key": entry.key,
                "author": entry.author,
                "title": entry.title,
                "year": entry.year,
                "type": entry.entry_type,
            }

            # Add optional fields if present
            if entry.journal:
                formatted_entry["journal"] = entry.journal
            if entry.volume:
                formatted_entry["volume"] = entry.volume
            if entry.pages:
                formatted_entry["pages"] = entry.pages
            if entry.publisher:
                formatted_entry["publisher"] = entry.publisher
            if entry.doi:
                formatted_entry["doi"] = entry.doi
            if entry.url:
                formatted_entry["url"] = entry.url

            formatted_bib.append(formatted_entry)

        return formatted_bib

    def _validate_document_integrity(
        self, document_structure: DocumentStructure, reference_map: ReferenceMap, citation_database: CitationDatabase
    ) -> None:
        """Perform additional validation and collect warnings."""

        # Check for empty sections
        for file_struct in document_structure.files:
            for section in file_struct.parsed_content.sections:
                if not section.content.strip():
                    self.warnings.append(f"Empty section '{section.title}' in {file_struct.relative_path}")

        # Check for unused bibliography entries
        cited_keys = set()
        for citation in citation_database.citations:
            cited_keys.update(citation.original_keys)

        unused_keys = set(citation_database.entries.keys()) - cited_keys
        if unused_keys:
            self.warnings.append(f"Unused bibliography entries: {', '.join(sorted(unused_keys))}")

        # Check for files with no sections
        for file_struct in document_structure.files:
            if not file_struct.parsed_content.sections:
                self.warnings.append(f"File with no sections: {file_struct.relative_path}")

        # Check for duplicate section IDs
        section_ids = {}
        for file_struct in document_structure.files:
            for section in file_struct.parsed_content.sections:
                if section.id in section_ids:
                    self.warnings.append(
                        f"Duplicate section ID '{section.id}' in {file_struct.relative_path} "
                        f"and {section_ids[section.id]}"
                    )
                else:
                    section_ids[section.id] = file_struct.relative_path

    def _process_footnotes(
        self, document_structure: DocumentStructure
    ) -> Tuple[List[FootnoteReference], List[FootnoteDefinition], List[str]]:
        """Process all footnotes from document structure, numbering and validating them."""
        all_refs = []
        all_defs = []
        orphaned = []

        # Collect all footnote references and definitions from all files
        ref_identifiers = set()
        def_identifiers = set()

        for file_struct in document_structure.files:
            parsed_content = file_struct.parsed_content

            # Collect references
            for ref in parsed_content.all_footnote_refs:
                ref_identifiers.add(ref.identifier)
                all_refs.append(ref)

            # Collect definitions
            for def_ in parsed_content.all_footnote_defs:
                def_identifiers.add(def_.identifier)
                all_defs.append(def_)

        # Find orphaned footnotes (references without definitions, definitions without references)
        orphaned_refs = ref_identifiers - def_identifiers
        orphaned_defs = def_identifiers - ref_identifiers

        for orphan in orphaned_refs:
            orphaned.append(f"Footnote reference [^{orphan}] has no definition")
        for orphan in orphaned_defs:
            orphaned.append(f"Footnote definition [^{orphan}] has no references")

        # Number footnotes in order of first appearance
        identifier_to_number = {}
        numbered_refs = []
        numbered_defs = []

        # Sort references by file order and line number to establish numbering
        all_refs.sort(key=lambda r: (r.line_number, r.position))

        next_number = 1
        for ref in all_refs:
            if ref.identifier not in identifier_to_number:
                identifier_to_number[ref.identifier] = next_number
                next_number += 1

            numbered_refs.append(
                FootnoteReference(
                    identifier=ref.identifier,
                    number=identifier_to_number[ref.identifier],
                    position=ref.position,
                    file_path=str(ref.line_number),  # Using line_number as placeholder for file_path
                )
            )

        # Create numbered definitions
        for def_ in all_defs:
            if def_.identifier in identifier_to_number:
                numbered_defs.append(
                    FootnoteDefinition(
                        identifier=def_.identifier,
                        number=identifier_to_number[def_.identifier],
                        content=def_.content,
                        file_path=str(def_.line_number),  # Using line_number as placeholder for file_path
                    )
                )

        return numbered_refs, numbered_defs, orphaned


def assemble_complete_document(
    document_structure: DocumentStructure,
    reference_map: ReferenceMap,
    citation_database: CitationDatabase,
    config: Optional[Config] = None,
) -> AssembledDocument:
    """
    Convenience function for complete document assembly.

    Args:
        document_structure: Hierarchical document structure
        reference_map: Resolved cross-references
        citation_database: Bibliography and citations
        config: Configuration object with document metadata

    Returns:
        AssembledDocument: Complete assembled document
    """
    assembler = DocumentAssembly(config)
    return assembler.assemble_document(document_structure, reference_map, citation_database)

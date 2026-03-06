"""
Doctor content ingestion module

Maps directly to the architecture diagram components:
- Content Ingestion (G) → Parsed Content (L)
- Structure Analysis (H) → Document Structure (N)
- Cross-Reference Tracking (I) → Reference Map (O)
- Bibliography Processing (J) → Citation Database (P)
- Document Assembly (K)

Data models have been moved to doctor.models for cleaner separation.
The models are re-exported here for backward compatibility.
"""

# Re-export processors (the actual ingestion logic)
from doctor.ingest.assembly import DocumentAssembly, assemble_complete_document
from doctor.ingest.bibliography import BibliographyProcessing
from doctor.ingest.content import ContentIngestion
from doctor.ingest.references import CrossReferenceTracking
from doctor.ingest.report import IngestionReport, generate_ingestion_report
from doctor.ingest.structure import StructureAnalysis, build_document_structure

# Re-export models for backward compatibility
# These are now defined in doctor.models but re-exported here
from doctor.models.assembly import AssembledDocument
from doctor.models.bibliography import BibliographyEntry, CitationDatabase, ProcessedCitation
from doctor.models.content import (
    Citation,
    FigureEmbed,
    FootnoteDef,
    FootnoteRef,
    FrontMatter,
    MathBlock,
    ParsedContent,
    Section,
    WikiLink,
)
from doctor.models.references import AssetReference, ReferenceMap, ResolvedReference
from doctor.models.structure import DocumentOutline, DocumentStructure, FileStructure, TocEntry


__all__ = [
    # Processors
    "ContentIngestion",
    "StructureAnalysis",
    "CrossReferenceTracking",
    "BibliographyProcessing",
    "DocumentAssembly",
    "IngestionReport",
    # Convenience functions
    "build_document_structure",
    "assemble_complete_document",
    "generate_ingestion_report",
    # Models (re-exported for backward compatibility)
    "ParsedContent",
    "FrontMatter",
    "MathBlock",
    "Citation",
    "WikiLink",
    "FigureEmbed",
    "FootnoteRef",
    "FootnoteDef",
    "Section",
    "DocumentStructure",
    "DocumentOutline",
    "FileStructure",
    "TocEntry",
    "ReferenceMap",
    "ResolvedReference",
    "AssetReference",
    "CitationDatabase",
    "BibliographyEntry",
    "ProcessedCitation",
    "AssembledDocument",
]

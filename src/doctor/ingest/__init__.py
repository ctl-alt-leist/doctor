"""
Doctor content ingestion module

Maps directly to the architecture diagram components:
- Content Ingestion (G) → Parsed Content (L)
- Structure Analysis (H) → Document Structure (N)
- Cross-Reference Tracking (I) → Reference Map (O)
- Bibliography Processing (J) → Citation Database (P)
- Document Assembly (K)
"""

from doctor.ingest.assembly import DocumentAssembly
from doctor.ingest.bibliography import BibliographyProcessing, CitationDatabase
from doctor.ingest.content import ContentIngestion, ParsedContent
from doctor.ingest.references import CrossReferenceTracking, ReferenceMap
from doctor.ingest.report import IngestionReport, generate_ingestion_report
from doctor.ingest.structure import DocumentStructure, StructureAnalysis


__all__ = [
    "ContentIngestion",
    "ParsedContent",
    "StructureAnalysis",
    "DocumentStructure",
    "CrossReferenceTracking",
    "ReferenceMap",
    "BibliographyProcessing",
    "CitationDatabase",
    "DocumentAssembly",
    "IngestionReport",
    "generate_ingestion_report",
]

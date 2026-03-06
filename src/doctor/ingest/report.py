"""
Ingestion Report Generator

Creates human-readable reports of the ingestion pipeline results for debugging
and inspection purposes.
"""

from pathlib import Path
from typing import Dict, List

from doctor.models.assembly import AssembledDocument
from doctor.models.bibliography import CitationDatabase
from doctor.models.references import ReferenceMap
from doctor.models.structure import DocumentStructure


class IngestionReport:
    """Generates formatted reports of ingestion pipeline results."""

    def __init__(self, indent: str = "  "):
        self.indent = indent

    def generate_report(self, assembled_doc: AssembledDocument) -> str:
        """Generate complete ingestion report."""
        lines = []

        lines.extend(self._report_header(assembled_doc))
        lines.extend(self._report_document_structure(assembled_doc.document_structure))
        lines.extend(self._report_references(assembled_doc.reference_map))
        lines.extend(self._report_bibliography(assembled_doc.citation_database))
        lines.extend(self._report_validation(assembled_doc))

        return "\n".join(lines)

    def _report_header(self, doc: AssembledDocument) -> List[str]:
        """Generate report header with metadata."""
        lines = [
            "=" * 80,
            "DOCTOR INGESTION PIPELINE REPORT",
            "=" * 80,
            "",
            f"Document Title: {doc.title}",
        ]

        if doc.author:
            lines.append(f"Author: {doc.author}")
        if doc.date:
            lines.append(f"Date: {doc.date}")

        lines.extend([
            "",
            "Summary Statistics:",
            f"{self.indent}Files processed: {doc.total_files}",
            f"{self.indent}Total sections: {doc.total_sections}",
            f"{self.indent}Cross-references: {doc.total_references}",
            f"{self.indent}Citations: {doc.total_citations}",
            f"{self.indent}Bibliography entries: {len(doc.bibliography)}",
            "",
        ])

        if doc.abstract:
            lines.extend([
                "Abstract:",
                f"{self.indent}{doc.abstract}",
                "",
            ])

        return lines

    def _report_document_structure(self, structure: DocumentStructure) -> List[str]:
        """Generate document structure section."""
        lines = [
            "-" * 80,
            "DOCUMENT STRUCTURE",
            "-" * 80,
            "",
        ]

        # High-level file categorization
        doc_files = []
        readme_files = []
        config_files = []
        other_files = []

        for file_struct in structure.files:
            path_str = str(file_struct.relative_path)
            if any(x in path_str.lower() for x in ["readme", "claude"]):
                readme_files.append(file_struct)
            elif any(x in path_str.lower() for x in ["config", ".toml"]):
                config_files.append(file_struct)
            elif path_str.endswith(".md") and not any(
                x in path_str for x in [".pytest_cache", ".venv", "site-packages"]
            ):
                doc_files.append(file_struct)
            else:
                other_files.append(file_struct)

        # Document files overview
        if doc_files:
            lines.append(f"Primary Documents ({len(doc_files)} files):")
            for file_struct in doc_files[:10]:  # Limit to first 10
                rel_path = file_struct.relative_path
                sections_count = len([s for s in file_struct.parsed_content.sections if s.level <= 3])
                main_sections = [s.title for s in file_struct.parsed_content.sections if s.level == 1][:3]
                lines.append(f"{self.indent}{rel_path}")
                if main_sections:
                    sections_str = ", ".join(main_sections)
                    if len(main_sections) >= 3:
                        sections_str += "..."
                    lines.append(f"{self.indent * 2}Main topics: {sections_str}")
                lines.append(f"{self.indent * 2}Sections: {sections_count}")
                lines.append("")

            if len(doc_files) > 10:
                lines.append(f"{self.indent}... and {len(doc_files) - 10} more documents")
                lines.append("")

        # README/Documentation files
        if readme_files:
            lines.append(f"Documentation/README files ({len(readme_files)}):")
            for file_struct in readme_files:
                lines.append(f"{self.indent}{file_struct.relative_path}")
            lines.append("")

        # Other files summary
        if config_files or other_files:
            total_other = len(config_files) + len(other_files)
            lines.append(f"Other files ({total_other}): configs, build artifacts, etc.")
            lines.append("")

        # Document hierarchy summary (simplified)
        lines.append("Document Hierarchy Summary:")
        try:
            # Get actual meaningful sections, not the broken TOC
            meaningful_sections = []
            for file_struct in doc_files[:5]:  # First 5 doc files only
                for section in file_struct.parsed_content.sections:
                    if (
                        section.level <= 2
                        and len(section.title) > 3
                        and not any(x in section.title.lower() for x in ["install", "setup", "run", "#"])
                    ):
                        meaningful_sections.append((file_struct.relative_path.stem, section.title, section.level))

            if meaningful_sections:
                for filename, title, level in meaningful_sections[:15]:  # Limit to 15
                    indent_str = self.indent * level
                    lines.append(f"{indent_str}[{filename}] {title}")

                if len(meaningful_sections) > 15:
                    lines.append(f"{self.indent}... and {len(meaningful_sections) - 15} more sections")
            else:
                lines.append(f"{self.indent}(Structure analysis needs debugging - TOC generation issues)")

        except Exception as e:
            lines.append(f"{self.indent}(Error generating hierarchy: {str(e)[:50]}...)")

        lines.append("")
        return lines

    def _report_references(self, ref_map: ReferenceMap) -> List[str]:
        """Generate cross-references section."""
        lines = [
            "-" * 80,
            "CROSS-REFERENCES & LINKS",
            "-" * 80,
            "",
        ]

        if not ref_map.resolved_references:
            lines.append("No cross-references found.")
            lines.append("")
            return lines

        # High-level summary by type
        by_type: Dict[str, List] = {}
        for ref in ref_map.resolved_references:
            ref_type = ref.reference_type
            if ref_type not in by_type:
                by_type[ref_type] = []
            by_type[ref_type].append(ref)

        # Summary statistics
        lines.append("Reference Summary:")
        total_refs = len(ref_map.resolved_references)
        valid_refs = len([r for r in ref_map.resolved_references if r.is_valid])
        total_refs - valid_refs

        for ref_type, refs in by_type.items():
            valid_count = len([r for r in refs if r.is_valid])
            broken_count = len(refs) - valid_count
            lines.append(
                f"{self.indent}{ref_type.title()}: {len(refs)} total ({valid_count} valid, {broken_count} broken)"
            )

        lines.append(f"{self.indent}Overall: {valid_refs}/{total_refs} references resolved successfully")
        lines.append("")

        # Show sample of broken references if any
        broken = ref_map.get_broken_references()
        if broken:
            lines.append("Sample Broken References:")
            unique_errors = {}
            for ref in broken:
                error_key = ref.error_message or "Unknown error"
                if error_key not in unique_errors:
                    unique_errors[error_key] = []
                unique_errors[error_key].append(ref.original_text)

            for error, examples in list(unique_errors.items())[:3]:  # Top 3 error types
                lines.append(f"{self.indent}{error}:")
                for example in examples[:2]:  # 2 examples each
                    lines.append(f"{self.indent * 2}• {example}")
                if len(examples) > 2:
                    lines.append(f"{self.indent * 2}• ... and {len(examples) - 2} more")
                lines.append("")

        return lines

    def _report_bibliography(self, citation_db: CitationDatabase) -> List[str]:
        """Generate bibliography section."""
        lines = [
            "-" * 80,
            "BIBLIOGRAPHY & CITATIONS",
            "-" * 80,
            "",
        ]

        # High-level citation summary
        total_citations = len(citation_db.citations)
        valid_citations = len([c for c in citation_db.citations if c.is_valid])
        total_bib_entries = len(citation_db.entries)

        if total_citations == 0 and total_bib_entries == 0:
            lines.append("No citations or bibliography entries found.")
            lines.append("")
            return lines

        lines.append("Citation Summary:")
        lines.append(f"{self.indent}Bibliography entries available: {total_bib_entries}")
        lines.append(f"{self.indent}Citations found in text: {total_citations}")
        lines.append(f"{self.indent}Successfully resolved: {valid_citations}/{total_citations}")
        lines.append("")

        # Sample bibliography entries if available
        if citation_db.entries:
            lines.append("Sample Bibliography Entries:")
            for key, entry in list(citation_db.entries.items())[:3]:  # First 3
                lines.append(f"{self.indent}[{key}] {entry.author} ({entry.year})")
                title_preview = entry.title[:60] + "..." if len(entry.title) > 60 else entry.title
                lines.append(f'{self.indent * 2}"{title_preview}"')
                if entry.journal:
                    lines.append(f"{self.indent * 2}{entry.journal}")
                lines.append("")

            if len(citation_db.entries) > 3:
                lines.append(f"{self.indent}... and {len(citation_db.entries) - 3} more entries")
                lines.append("")

        # Citation issues summary
        missing_citations = citation_db.get_missing_citations()
        if missing_citations:
            lines.append(f"Citation Issues ({len(missing_citations)} unresolved):")

            # Group by missing keys
            missing_keys = set()
            for citation in missing_citations:
                missing_keys.update(citation.missing_keys)

            if missing_keys:
                lines.append(f"{self.indent}Missing bibliography keys:")
                for key in list(missing_keys)[:5]:  # First 5
                    lines.append(f"{self.indent * 2}• {key}")
                if len(missing_keys) > 5:
                    lines.append(f"{self.indent * 2}• ... and {len(missing_keys) - 5} more")
                lines.append("")

        return lines

    def _report_validation(self, doc: AssembledDocument) -> List[str]:
        """Generate validation section."""
        lines = [
            "-" * 80,
            "PROCESSING SUMMARY",
            "-" * 80,
            "",
        ]

        # Overall status
        if doc.is_valid:
            lines.append("✓ Document processed successfully - no critical issues")
        else:
            lines.append("⚠ Document processed with some issues")

        lines.append("")

        # High-level statistics
        summary = doc.validation_summary
        lines.extend([
            "Processing Results:",
            f"{self.indent}Files processed: {summary['total_files']}",
            f"{self.indent}Sections extracted: {summary['total_sections']}",
            f"{self.indent}Cross-references found: {summary['total_references']}",
            f"{self.indent}Citations discovered: {summary['total_citations']}",
            "",
        ])

        # Issue summary
        total_issues = summary["broken_references"] + summary["missing_citations"] + summary["warnings"]
        if total_issues > 0:
            lines.extend([
                "Issues Found:",
                f"{self.indent}Broken links/references: {summary['broken_references']}",
                f"{self.indent}Missing bibliography entries: {summary['missing_citations']}",
                f"{self.indent}Processing warnings: {summary['warnings']}",
                "",
            ])

            # Brief issue examples
            if doc.broken_references:
                lines.append("Sample Issues:")
                lines.append(f"{self.indent}Broken references: {doc.broken_references[0].original_text}...")

            if doc.missing_citations:
                sample_keys = ", ".join(doc.missing_citations[0].missing_keys[:2])
                lines.append(f"{self.indent}Missing citations: {sample_keys}...")

            if doc.validation_warnings:
                lines.append(f"{self.indent}Warnings: {doc.validation_warnings[0][:50]}...")

            lines.append("")
            lines.append("Note: Use --verbose for detailed issue listings")
        else:
            lines.append("No processing issues found.")

        lines.append("")
        lines.append("=" * 80)
        return lines

    def write_report_file(self, assembled_doc: AssembledDocument, output_path: Path) -> None:
        """Write report to file."""
        report_content = self.generate_report(assembled_doc)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

    def print_report(self, assembled_doc: AssembledDocument) -> None:
        """Print report to stdout."""
        print(self.generate_report(assembled_doc))


def generate_ingestion_report(assembled_doc: AssembledDocument, output_path: Path = None) -> str:
    """
    Convenience function to generate ingestion report.

    Args:
        assembled_doc: Complete assembled document
        output_path: Optional file path to write report

    Returns:
        str: Report content
    """
    reporter = IngestionReport()
    report_content = reporter.generate_report(assembled_doc)

    if output_path:
        reporter.write_report_file(assembled_doc, output_path)

    return report_content

"""
Test the complete ingestion pipeline with the test project.

This test validates that all components work together:
- File discovery → Content ingestion → Structure analysis → Reference tracking → Bibliography processing → Assembly
"""

from pathlib import Path

import pytest

from doctor.discovery import discover_project_files
from doctor.ingest.assembly import DocumentAssembly
from doctor.ingest.bibliography import BibliographyProcessing
from doctor.ingest.content import ContentIngestion
from doctor.ingest.references import CrossReferenceTracking
from doctor.ingest.structure import StructureAnalysis


class TestIngestionPipeline:
    """Test complete ingestion pipeline with test project."""

    def test_complete_pipeline_with_test_project(self):
        """Test full pipeline: discovery → ingestion → structure → references → bibliography → assembly."""
        # Use the test project
        test_project_path = Path(__file__).parent.parent.parent / "docs" / "test-project"

        if not test_project_path.exists():
            pytest.skip(f"Test project not found at {test_project_path}")

        # Step 1: File Discovery
        file_structure = discover_project_files(test_project_path)
        assert file_structure.total_files > 0, "Should discover markdown files"

        # Step 2: Content Ingestion (G → L)
        content_ingestion = ContentIngestion()
        parsed_files = []

        for md_file in file_structure.files:
            parsed_content = content_ingestion.ingest_file(md_file)
            parsed_files.append(parsed_content)

        assert len(parsed_files) > 0, "Should parse files successfully"

        # Step 3: Structure Analysis (H → N)
        structure_analysis = StructureAnalysis()
        document_structure = structure_analysis.analyze_files(parsed_files)

        assert document_structure.total_files == len(parsed_files)
        assert document_structure.total_sections > 0, "Should find sections in documents"

        # Step 4: Cross-Reference Tracking (I → O)
        reference_tracking = CrossReferenceTracking(test_project_path)
        reference_map = reference_tracking.track_references(document_structure)

        # Should handle references (even if none exist)
        assert reference_map.total_references >= 0

        # Step 5: Bibliography Processing (J → P)
        references_file = test_project_path / "references.toml"
        bibliography_processing = BibliographyProcessing()
        citation_database = bibliography_processing.process_bibliography(
            parsed_files, [references_file] if references_file.exists() else None
        )

        # Should handle citations (even if none exist)
        assert citation_database.total_citations >= 0

        # Step 6: Document Assembly (K)
        document_assembly = DocumentAssembly()
        assembled_document = document_assembly.assemble_document(document_structure, reference_map, citation_database)

        # Validate final assembled document
        assert assembled_document.title is not None
        assert assembled_document.total_files > 0
        assert len(assembled_document.table_of_contents) >= 0

        # Print summary for inspection
        print("\n=== Ingestion Pipeline Results ===")
        print(f"Files processed: {assembled_document.total_files}")
        print(f"Sections found: {assembled_document.total_sections}")
        print(f"References tracked: {assembled_document.total_references}")
        print(f"Citations processed: {assembled_document.total_citations}")
        print(f"Document title: {assembled_document.title}")
        print(f"Valid document: {assembled_document.is_valid}")

        if assembled_document.validation_warnings:
            print(f"Warnings: {len(assembled_document.validation_warnings)}")
            for warning in assembled_document.validation_warnings:
                print(f"  - {warning}")

    def test_content_parsing_with_math_and_citations(self):
        """Test that math blocks and citations are properly extracted."""
        test_project_path = Path(__file__).parent.parent.parent / "docs" / "test-project"

        if not test_project_path.exists():
            pytest.skip(f"Test project not found at {test_project_path}")

        # Find the Mathematical Foundations file
        file_structure = discover_project_files(test_project_path)
        math_file = None

        for md_file in file_structure.files:
            if "Mathematical Foundations" in md_file.name:
                math_file = md_file
                break

        if not math_file:
            pytest.skip("Mathematical Foundations file not found")

        # Parse the file with math content
        content_ingestion = ContentIngestion()
        parsed_content = content_ingestion.ingest_file(math_file)

        # Should find math blocks
        assert len(parsed_content.all_math_blocks) > 0, "Should find LaTeX math blocks"

        # Check for display math ($$...$$)
        display_math = [m for m in parsed_content.all_math_blocks if m.display]
        assert len(display_math) > 0, "Should find display math blocks"

        # Should find citations
        assert len(parsed_content.all_citations) > 0, "Should find citation references"

        # Verify citation format
        citation_keys = []
        for citation in parsed_content.all_citations:
            citation_keys.extend(citation.keys)

        assert len(citation_keys) > 0, "Should extract citation keys"
        print(f"Found citation keys: {citation_keys}")

    def test_frontmatter_extraction(self):
        """Test YAML frontmatter extraction from a chapter file."""
        test_project_path = Path(__file__).parent.parent.parent / "docs" / "test-project"

        if not test_project_path.exists():
            pytest.skip(f"Test project not found at {test_project_path}")

        # A chapter file carries frontmatter (README is repo docs, ignored)
        fm_path = test_project_path / "1. Introduction" / "1. Historical Context.md"
        if not fm_path.exists():
            pytest.skip("Frontmatter fixture file not found in test project")

        from doctor.discovery import MarkdownFile

        # Create MarkdownFile and load content
        fm_file = MarkdownFile(
            path=fm_path,
            relative_path=fm_path.relative_to(test_project_path),
            name=fm_path.name,
            parent_dir="1. Introduction",
        )

        # Parse the file
        content_ingestion = ContentIngestion()
        parsed_content = content_ingestion.ingest_file(fm_file)

        # Should extract frontmatter
        frontmatter = parsed_content.frontmatter
        assert frontmatter.title is not None, "Should extract title from frontmatter"
        assert frontmatter.author is not None, "Should extract author from frontmatter"
        assert frontmatter.date is not None, "Should extract date from frontmatter"

        print(
            f"Extracted frontmatter: title='{frontmatter.title}', "
            f"author='{frontmatter.author}', date='{frontmatter.date}'"
        )


if __name__ == "__main__":
    # Run the test directly
    test = TestIngestionPipeline()
    test.test_complete_pipeline_with_test_project()
    test.test_content_parsing_with_math_and_citations()
    test.test_frontmatter_extraction()

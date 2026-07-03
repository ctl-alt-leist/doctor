"""
Feature validation tests to demonstrate all ingestion capabilities.

These tests showcase the specific features working with the test project.
"""

from pathlib import Path

import pytest

from doctor.discovery import discover_project_files
from doctor.ingest.assembly import DocumentAssembly
from doctor.ingest.bibliography import BibliographyProcessing
from doctor.ingest.content import ContentIngestion
from doctor.ingest.references import CrossReferenceTracking
from doctor.ingest.structure import StructureAnalysis


class TestFeatureValidation:
    """Validate all ingestion features are working with test project."""

    @pytest.fixture
    def test_project_path(self):
        """Get path to test project."""
        path = Path(__file__).parent.parent.parent / "docs" / "test-project"
        if not path.exists():
            pytest.skip(f"Test project not found at {path}")
        return path

    def full_pipeline_result(self, test_project_path):
        """Run complete pipeline and return assembled document."""
        # Discovery
        file_structure = discover_project_files(test_project_path)

        # Content Ingestion
        content_ingestion = ContentIngestion()
        parsed_files = []
        for md_file in file_structure.files:
            parsed_content = content_ingestion.ingest_file(md_file)
            parsed_files.append(parsed_content)

        # Structure Analysis
        structure_analysis = StructureAnalysis()
        document_structure = structure_analysis.analyze_files(parsed_files)

        # Reference Tracking
        reference_tracking = CrossReferenceTracking(test_project_path)
        reference_map = reference_tracking.track_references(document_structure)

        # Bibliography Processing
        references_file = test_project_path / "references.toml"
        bibliography_processing = BibliographyProcessing()
        citation_database = bibliography_processing.process_bibliography(
            parsed_files, [references_file] if references_file.exists() else None
        )

        # Document Assembly
        document_assembly = DocumentAssembly()
        return document_assembly.assemble_document(document_structure, reference_map, citation_database)

    def test_file_discovery_working(self, test_project_path):
        """Test that file discovery finds all expected files."""
        file_structure = discover_project_files(test_project_path)

        # Should find the 6 chapter markdown files; README.md is ignored
        assert file_structure.total_files == 6

        # Verify specific files exist, and that README is excluded
        file_names = [f.name for f in file_structure.files]
        assert "README.md" not in file_names
        assert "1. Mathematical Foundations.md" in file_names
        assert "2. Feynman Diagrams.md" in file_names

        print(f"✓ Discovered {file_structure.total_files} files in {len(file_structure.directories)} directories")

    def test_yaml_frontmatter_extraction(self, test_project_path):
        """Test YAML frontmatter extraction from a chapter file."""
        file_structure = discover_project_files(test_project_path)

        # Find the chapter file that carries frontmatter
        fm_file = None
        for f in file_structure.files:
            if f.name == "1. Historical Context.md":
                fm_file = f
                break

        assert fm_file is not None, "Historical Context file should be found"

        # Parse frontmatter
        content_ingestion = ContentIngestion()
        parsed_content = content_ingestion.ingest_file(fm_file)

        frontmatter = parsed_content.frontmatter
        assert frontmatter.title == "Historical Context"
        assert frontmatter.author == "Dr. Jane Smith"
        assert frontmatter.date == "2025"
        assert "quantum field theory" in frontmatter.abstract.lower()

        print(f"✓ Extracted frontmatter: {frontmatter.title} by {frontmatter.author}")

    def test_latex_math_extraction(self, test_project_path):
        """Test LaTeX math block extraction."""
        file_structure = discover_project_files(test_project_path)

        # Find Mathematical Foundations file
        math_file = None
        for f in file_structure.files:
            if "Mathematical Foundations" in f.name:
                math_file = f
                break

        assert math_file is not None, "Mathematical Foundations file should be found"

        # Parse math content
        content_ingestion = ContentIngestion()
        parsed_content = content_ingestion.ingest_file(math_file)

        # Should find both display and inline math
        math_blocks = parsed_content.all_math_blocks
        assert len(math_blocks) > 10, "Should find multiple math blocks"

        # Check for specific equations
        math_content = [m.content for m in math_blocks]
        lagrangian_found = any("mathcal{L}" in content for content in math_content)
        commutator_found = any("delta^3" in content for content in math_content)

        assert lagrangian_found, "Should find Lagrangian equation"
        assert commutator_found, "Should find commutator relations"

        display_math_count = len([m for m in math_blocks if m.display])
        inline_math_count = len([m for m in math_blocks if not m.display])

        print(f"✓ Found {display_math_count} display math, {inline_math_count} inline math blocks")

    def test_citation_processing(self, test_project_path):
        """Test citation extraction and bibliography resolution."""
        file_structure = discover_project_files(test_project_path)

        # Parse all files
        content_ingestion = ContentIngestion()
        parsed_files = []
        for md_file in file_structure.files:
            parsed_content = content_ingestion.ingest_file(md_file)
            parsed_files.append(parsed_content)

        # Process bibliography
        references_file = test_project_path / "references.toml"
        bibliography_processing = BibliographyProcessing()
        citation_database = bibliography_processing.process_bibliography(parsed_files, [references_file])

        # Should find citations
        assert citation_database.total_citations > 0, "Should find citations in documents"

        # Should load bibliography entries
        assert len(citation_database.entries) > 0, "Should load bibliography entries"

        # Verify specific entries exist
        assert "weinberg-1995-a" in citation_database.entries
        assert "hawking-1975-a" in citation_database.entries

        # Check citation resolution
        valid_citations = [c for c in citation_database.citations if c.is_valid]
        assert len(valid_citations) > 0, "Should have valid resolved citations"

        print(
            f"✓ Processed {citation_database.total_citations} citations, "
            f"{len(citation_database.entries)} bibliography entries"
        )

    def test_hierarchical_document_structure(self, test_project_path):
        """Test document structure and table of contents generation."""
        assembled_doc = self.full_pipeline_result(test_project_path)

        # Should have proper document structure (6 chapter files; README ignored)
        assert assembled_doc.total_files == 6
        assert assembled_doc.total_sections > 40, "Should find many sections"

        # Should have table of contents
        toc = assembled_doc.table_of_contents
        assert len(toc) > 0, "Should generate table of contents"

        # Check for hierarchical numbering
        toc_numbers = [entry.number for entry in toc if entry.number]
        hierarchical_numbers = [num for num in toc_numbers if "." in num]
        assert len(hierarchical_numbers) > 0, "Should have hierarchical section numbers"

        # Verify specific sections exist
        section_titles = [entry.title for entry in toc]
        assert "Mathematical Foundations" in section_titles
        assert "From Classical to Quantum Fields" in section_titles

        print(f"✓ Generated TOC with {len(toc)} entries, hierarchical numbering working")

    def test_document_validation(self, test_project_path):
        """Test document validation and warning generation."""
        assembled_doc = self.full_pipeline_result(test_project_path)

        # Should generate validation warnings for empty sections
        warnings = assembled_doc.validation_warnings
        assert len(warnings) > 0, "Should generate warnings for document issues"

        # Verify specific warning types
        empty_section_warnings = [w for w in warnings if "Empty section" in w]

        assert len(empty_section_warnings) > 0, "Should warn about empty sections"
        # Note: All bibliography entries in the test project are used, so no unused warnings expected

        # Document metadata should be extracted
        assert assembled_doc.title is not None
        # Note: Author/date may not be extracted from all files, just verify title exists
        print(f"  - Document title: '{assembled_doc.title}'")

        print(f"✓ Document validation found {len(warnings)} warnings")

    def test_complete_pipeline_integration(self, test_project_path):
        """Test that all pipeline components integrate correctly."""
        assembled_doc = self.full_pipeline_result(test_project_path)

        # All major components should be present
        assert assembled_doc.document_structure is not None
        assert assembled_doc.reference_map is not None
        assert assembled_doc.citation_database is not None

        # Statistics should be reasonable
        stats = assembled_doc.validation_summary
        assert stats["total_files"] == 6
        assert stats["total_sections"] > 40
        assert stats["total_citations"] > 0

        # Should be ready for template rendering
        assert len(assembled_doc.table_of_contents) > 0
        assert len(assembled_doc.bibliography) > 0

        print("✓ Complete pipeline integration successful")
        print(f"  - Files: {stats['total_files']}, Sections: {stats['total_sections']}")
        print(f"  - Citations: {stats['total_citations']}, References: {stats['total_references']}")
        print(f"  - Bibliography entries: {len(assembled_doc.bibliography)}")


if __name__ == "__main__":
    # Run feature validation
    import sys

    test_project_path = Path(__file__).parent.parent.parent / "docs" / "test-project"
    if not test_project_path.exists():
        print(f"❌ Test project not found at {test_project_path}")
        sys.exit(1)

    test = TestFeatureValidation()

    print("=== Doctor Ingestion Feature Validation ===\n")

    # Run all validation tests
    test.test_file_discovery_working(test_project_path)
    test.test_yaml_frontmatter_extraction(test_project_path)
    test.test_latex_math_extraction(test_project_path)
    test.test_citation_processing(test_project_path)

    # Run pipeline tests
    pipeline_result = test.full_pipeline_result(test_project_path)
    test.test_hierarchical_document_structure(pipeline_result)
    test.test_document_validation(pipeline_result)
    test.test_complete_pipeline_integration(pipeline_result)

    print("\n🎉 All features validated successfully!")

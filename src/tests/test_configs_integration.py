"""
Integration tests for configuration loading
Test the complete config loading workflow with real files
"""

import tempfile
from pathlib import Path

import toml

from doctor.configs import load_config


class TestConfigIntegration:
    """Test configuration loading with realistic scenarios."""

    def test_load_defaults_only(self):
        """Test loading just the default configurations."""
        config = load_config()

        # Verify all major sections are loaded
        assert config.document.type == "article"  # Default type
        assert config.bibliography.style == "nature"  # Default style
        assert config.math.renderer == "mathjax"  # Default renderer
        assert config.layout.paper_size == "a4"  # Default paper
        assert config.typography.base_size == "16px"  # Default size

        # Verify complex nested defaults work
        assert len(config.typography.fonts.serif) > 0
        assert config.layout.margins.top == "2.5cm"
        assert config.figures.default_width == "80%"

    def test_project_config_override(self):
        """Test loading with a project-level doctor.toml file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            config_file = project_dir / "doctor.toml"

            # Create a sample project config
            project_config = {
                "document": {"type": "thesis", "title": "My PhD Thesis", "authors": ["Jane Doe"]},
                "typography": {"base_size": "12px"},
                "bibliography": {"style": "ieee"},
            }

            with open(config_file, "w") as f:
                toml.dump(project_config, f)

            # Load config
            config = load_config([config_file])

            # Verify overrides work
            assert config.document.type == "thesis"
            assert config.document.title == "My PhD Thesis"
            assert config.document.authors == ["Jane Doe"]
            assert config.typography.base_size == "12px"
            assert config.bibliography.style == "ieee"

            # Verify defaults still present where not overridden
            assert config.math.renderer == "mathjax"  # Default
            assert config.layout.paper_size == "a4"  # Default
            assert len(config.typography.fonts.serif) > 0  # Default fonts

    def test_multiple_config_files(self):
        """Test loading multiple configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create first config file (document settings)
            doc_config = temp_path / "document.toml"
            with open(doc_config, "w") as f:
                toml.dump({"document": {"type": "book", "title": "My Book"}}, f)

            # Create second config file (typography settings)
            typo_config = temp_path / "typography.toml"
            with open(typo_config, "w") as f:
                toml.dump({"typography": {"base_size": "14px", "fonts": {"serif": ["Times", "serif"]}}}, f)

            # Load both configs
            config = load_config([doc_config, typo_config])

            # Verify both files were loaded and merged
            assert config.document.type == "book"
            assert config.document.title == "My Book"
            assert config.typography.base_size == "14px"
            assert config.typography.fonts.serif == ["Times", "serif"]

            # Other defaults should remain
            assert config.bibliography.style == "nature"
            assert len(config.typography.fonts.sans) > 0  # Default sans fonts

    def test_deep_merge_behavior(self):
        """Test that nested configuration merging works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_file = temp_path / "partial.toml"

            # Override just part of nested structure
            partial_config = {
                "layout": {
                    "margins": {
                        "top": "5cm",  # Override just top margin
                        "inner": "4cm",  # Override just inner margin
                    },
                    "web": {
                        "max_width": "900px"  # Override just max_width
                    },
                }
            }

            with open(config_file, "w") as f:
                toml.dump(partial_config, f)

            config = load_config([config_file])

            # Verify overridden values
            assert config.layout.margins.top == "5cm"
            assert config.layout.margins.inner == "4cm"
            assert config.layout.web.max_width == "900px"

            # Verify non-overridden values remain default
            assert config.layout.margins.bottom == "2.5cm"  # Default
            assert config.layout.margins.left == "2.5cm"  # Default
            assert config.layout.web.responsive  # Default

    def test_validation_catches_errors(self):
        """Test that Pydantic validation catches configuration errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test invalid enum value (document.type is now an open profile name;
            # bibliography.style is still a constrained enum)
            invalid_config = temp_path / "invalid.toml"
            with open(invalid_config, "w") as f:
                toml.dump(
                    {
                        "bibliography": {
                            "style": "invalid_style"  # Not a valid CitationStyle
                        }
                    },
                    f,
                )

            try:
                load_config([invalid_config])
                raise AssertionError("Should have raised ValueError")
            except ValueError as e:
                assert "Invalid configuration" in str(e)

    def test_config_summary_function(self):
        """Test the configuration summary helper function."""
        from doctor.configs.loader import get_config_summary

        config = load_config()
        summary = get_config_summary(config)

        # Verify summary contains expected keys
        expected_keys = [
            "document_type",
            "output_formats",
            "citation_style",
            "math_renderer",
            "paper_size",
            "font_serif",
            "font_sans",
        ]

        for key in expected_keys:
            assert key in summary

        # Verify values are reasonable
        assert summary["document_type"] == "article"
        assert summary["citation_style"] == "nature"
        assert summary["math_renderer"] == "mathjax"
        assert summary["paper_size"] == "a4"

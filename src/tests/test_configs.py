"""
Unit tests for configuration loading
Simple tests to ensure configs can be loaded properly
"""

import tempfile
from pathlib import Path

import pytest
import toml

from doctor.configs import Config, load_config, load_defaults
from doctor.configs.models import CitationStyle, DocumentType, MathRenderer


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_defaults(self):
        """Test that default configurations can be loaded."""
        defaults = load_defaults()

        # Should have all major sections
        assert "document" in defaults
        assert "typography" in defaults
        assert "layout" in defaults
        assert "math" in defaults
        assert "bibliography" in defaults
        assert "figures" in defaults
        assert "output" in defaults

    def test_create_config_from_defaults(self):
        """Test creating a Config object from defaults only."""
        config = load_config()

        # Test basic structure
        assert isinstance(config, Config)
        assert config.document.type == DocumentType.ARTICLE
        assert config.bibliography.style == CitationStyle.NATURE
        assert config.math.renderer == MathRenderer.MATHJAX

        # Test default values
        assert config.layout.paper_size == "a4"
        assert config.typography.base_size == "16px"
        assert len(config.typography.fonts.serif) > 0

    def test_config_with_user_override(self):
        """Test configuration with user overrides."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Create a simple user config
            user_config = {"document": {"type": "book", "title": "My Test Book"}, "bibliography": {"style": "apa"}}
            toml.dump(user_config, f)
            f.flush()

            user_config_path = Path(f.name)

        try:
            config = load_config([user_config_path])

            # User overrides should be applied
            assert config.document.type == DocumentType.BOOK
            assert config.document.title == "My Test Book"
            assert config.bibliography.style == CitationStyle.APA

            # Defaults should still be present where not overridden
            assert config.math.renderer == MathRenderer.MATHJAX
            assert len(config.typography.fonts.serif) > 0

        finally:
            user_config_path.unlink()  # Clean up

    def test_deep_merge_behavior(self):
        """Test that nested configurations merge properly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Override just part of typography config
            user_config = {"typography": {"base_size": "18px", "fonts": {"serif": ["Times New Roman", "serif"]}}}
            toml.dump(user_config, f)
            f.flush()

            user_config_path = Path(f.name)

        try:
            config = load_config([user_config_path])

            # Overridden values
            assert config.typography.base_size == "18px"
            assert config.typography.fonts.serif == ["Times New Roman", "serif"]

            # Non-overridden values should remain
            assert config.typography.line_height == 1.15  # Default value
            assert len(config.typography.fonts.sans) > 0  # Default fonts

        finally:
            user_config_path.unlink()

    def test_multiple_user_configs(self):
        """Test loading multiple user configuration files."""
        # Create first config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f1:
            config1 = {"document": {"type": "thesis", "title": "My Thesis"}}
            toml.dump(config1, f1)
            f1.flush()
            config1_path = Path(f1.name)

        # Create second config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f2:
            config2 = {"document": {"authors": ["John Doe"]}, "bibliography": {"style": "ieee"}}
            toml.dump(config2, f2)
            f2.flush()
            config2_path = Path(f2.name)

        try:
            config = load_config([config1_path, config2_path])

            # Both configs should be merged
            assert config.document.type == DocumentType.THESIS
            assert config.document.title == "My Thesis"
            assert config.document.authors == ["John Doe"]
            assert config.bibliography.style == CitationStyle.IEEE

        finally:
            config1_path.unlink()
            config2_path.unlink()

    def test_invalid_config_raises_error(self):
        """Test that invalid configurations raise appropriate errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Invalid citation style (document.type is now an open profile name)
            user_config = {"bibliography": {"style": "invalid_style"}}
            toml.dump(user_config, f)
            f.flush()

            user_config_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                load_config([user_config_path])

        finally:
            user_config_path.unlink()

    def test_missing_config_file_raises_error(self):
        """Test that missing configuration files raise FileNotFoundError."""
        nonexistent_path = Path("/nonexistent/config.toml")

        with pytest.raises(FileNotFoundError):
            load_config([nonexistent_path])

    def test_malformed_toml_raises_error(self):
        """Test that malformed TOML files raise appropriate errors."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            # Invalid TOML syntax
            f.write("invalid [ toml syntax")
            f.flush()

            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError):
                load_config([config_path])

        finally:
            config_path.unlink()


class TestConfigValidation:
    """Test Pydantic model validation."""

    def test_config_model_validation(self):
        """Test that Config model validates correctly."""
        # Valid config data
        config_data = {"document": {"type": "article", "title": "Test Article"}, "typography": {"base_size": "16px"}}

        config = Config(**config_data)
        assert config.document.type == DocumentType.ARTICLE
        assert config.document.title == "Test Article"

    def test_enum_validation(self):
        """Test that enum values are validated (document.type is now an open string)."""
        with pytest.raises(ValueError):
            Config(bibliography={"style": "invalid_style"})

    def test_field_validation(self):
        """Test that field constraints are enforced."""
        with pytest.raises(ValueError):
            # scale_ratio must be > 1.0
            Config(typography={"scale_ratio": 0.5})

        with pytest.raises(ValueError):
            # numbering_depth must be between 0 and 6
            Config(document={"structure": {"numbering_depth": 10}})

"""
Configuration loading with defaults fallback
Loads TOML configuration files and merges with defaults

Supports hierarchical configuration via 'extends' field:
    extends = "../doctor.toml"  # Inherit from parent config
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import toml

from doctor.configs.models import Config


# Track config file location for relative path resolution
_config_base_path: Optional[Path] = None


def get_config_base_path() -> Optional[Path]:
    """Get the base path for resolving relative paths in config."""
    return _config_base_path


def set_config_base_path(path: Optional[Path]) -> None:
    """Set the base path for resolving relative paths in config."""
    global _config_base_path
    _config_base_path = path


def get_defaults_dir() -> Path:
    """Get the path to the default configuration directory."""
    # In development, use the configs/defaults directory
    current_file = Path(__file__)
    repo_root = current_file.parent.parent.parent.parent
    defaults_dir = repo_root / "configs" / "defaults"

    if defaults_dir.exists():
        return defaults_dir

    # Fallback for packaged installation
    # This would be implemented for production packaging
    raise FileNotFoundError("Cannot find default configuration directory")


def load_toml_file(file_path: Path) -> Dict[str, Any]:
    """Load a TOML file and return parsed data."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except toml.TomlDecodeError as e:
        raise ValueError(f"Invalid TOML syntax in {file_path}: {e}") from e
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Configuration file not found: {file_path}") from e
    except Exception as e:
        raise RuntimeError(f"Error loading {file_path}: {e}") from e


def load_defaults() -> Dict[str, Any]:
    """Load all default configuration files."""
    defaults_dir = get_defaults_dir()

    # Default configuration files in order of loading
    default_files = [
        "document.toml",
        "typography.toml",
        "layout.toml",
        "math.toml",
        "bibliography.toml",
        "figures.toml",
        "output.toml",
    ]

    merged_config = {}

    for filename in default_files:
        file_path = defaults_dir / filename
        if file_path.exists():
            config_data = load_toml_file(file_path)
            merged_config = deep_merge(merged_config, config_data)

    return merged_config


def load_config_with_extends(
    config_path: Path, seen_paths: Optional[Set[Path]] = None
) -> Dict[str, Any]:
    """
    Load a config file, recursively loading any extended configs first.

    Args:
        config_path: Path to the config file
        seen_paths: Set of already-seen paths to detect circular dependencies

    Returns:
        Merged configuration dictionary with inherited values
    """
    if seen_paths is None:
        seen_paths = set()

    # Resolve to absolute path
    config_path = config_path.resolve()

    # Check for circular dependencies
    if config_path in seen_paths:
        raise ValueError(f"Circular config dependency detected: {config_path}")
    seen_paths.add(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config_data = load_toml_file(config_path)

    # Check for 'extends' field
    extends = config_data.pop("extends", None)

    if extends:
        # Resolve relative path from the config file's directory
        if isinstance(extends, str):
            extends_paths = [extends]
        else:
            extends_paths = extends

        # Load parent configs first
        parent_config = {}
        for extend_path_str in extends_paths:
            extend_path = Path(extend_path_str)
            if not extend_path.is_absolute():
                extend_path = config_path.parent / extend_path
            extend_path = extend_path.resolve()

            parent_data = load_config_with_extends(extend_path, seen_paths.copy())
            parent_config = deep_merge(parent_config, parent_data)

        # Child config overrides parent
        config_data = deep_merge(parent_config, config_data)

    return config_data


def load_user_configs(configs_paths: List[Path]) -> Dict[str, Any]:
    """Load user configurations files with extends support."""
    merged_config = {}

    for config_path in configs_paths:
        config_data = load_config_with_extends(config_path)
        merged_config = deep_merge(merged_config, config_data)

    return merged_config


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    Values in 'update' override values in 'base'.
    """
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_configs(configs_paths: Optional[List[Path]] = None, project_path: Optional[Path] = None) -> Config:
    """
    Load configuration with defaults fallback.

    Args:
        configs_paths: List of user configuration file paths.
                      If None or empty, only defaults are loaded.
        project_path: Project directory for resolving relative paths.

    Returns:
        Config: Validated configuration object

    Raises:
        FileNotFoundError: If configuration files are not found
        ValueError: If configuration is invalid
    """
    # Start with defaults
    config_data = load_defaults()

    # Track the primary config path for relative path resolution
    primary_config_path = None
    if configs_paths:
        # Use the first (primary) config file's directory as base
        primary_config_path = configs_paths[0].resolve().parent
        set_config_base_path(primary_config_path)
    elif project_path:
        set_config_base_path(project_path.resolve())

    # Merge with user configurations
    if configs_paths:
        user_config = load_user_configs(configs_paths)
        config_data = deep_merge(config_data, user_config)

    # Validate and create Config object
    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}") from e


def resolve_config_path(relative_path: str) -> Path:
    """
    Resolve a relative path from a config file to an absolute path.

    Args:
        relative_path: Path string from config (e.g., "../references.toml")

    Returns:
        Absolute path resolved from config base path
    """
    path = Path(relative_path)
    if path.is_absolute():
        return path

    base_path = get_config_base_path()
    if base_path:
        return (base_path / path).resolve()

    # Fallback: resolve from current directory
    return path.resolve()


def apply_document_type_presets(config: Config) -> Config:
    """
    Apply document type presets to override specific settings.
    This handles the preset configurations defined in the TOML files.
    """
    doc_type = config.document.type

    # Apply document type specific settings
    if doc_type == "article":
        # Article presets
        config.document.structure.include_toc = False
        config.document.chapters.enabled = False
        config.layout.web.max_width = "700px"
        config.typography.line_height = 1.1
        config.typography.paragraph_spacing = "0.25rem"
        config.layout.spacing.section_spacing = "1.5rem"

    elif doc_type == "book":
        # Book presets
        config.document.structure.include_toc = True
        config.document.structure.include_lot = True
        config.document.structure.include_lof = True
        config.document.chapters.enabled = True
        config.layout.web.max_width = "800px"
        config.typography.line_height = 1.2
        config.typography.paragraph_spacing = "0.75rem"
        config.typography.paragraph_indent = "2rem"

    elif doc_type == "thesis":
        # Thesis presets
        config.document.structure.include_toc = True
        config.document.structure.include_lot = True
        config.document.structure.include_lof = True
        config.document.chapters.enabled = True
        config.layout.margins.top = "3.5cm"
        config.layout.margins.inner = "3.5cm"
        config.layout.web.max_width = "850px"
        config.typography.line_height = 1.25
        config.typography.paragraph_spacing = "1rem"
        config.typography.paragraph_indent = "2rem"

    return config


def get_config_summary(config: Config) -> Dict[str, Any]:
    """Get a summary of the current configuration for debugging."""
    return {
        "document_type": config.document.type,
        "output_formats": config.output.formats,
        "citation_style": config.bibliography.style,
        "math_renderer": config.math.renderer,
        "paper_size": config.layout.paper_size,
        "font_serif": config.typography.fonts.serif[0] if config.typography.fonts.serif else "default",
        "font_sans": config.typography.fonts.sans[0] if config.typography.fonts.sans else "default",
    }


# Backwards compatibility alias
load_config = load_configs

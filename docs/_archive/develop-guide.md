# Doctor Development Guide

This document contains coding conventions, development practices, and nitpicks to maintain code quality and consistency throughout the project. **Update this document as new conventions are established.**

## Development Workflow

### Always Run Linting
- **MUST** run `make lint` after any code changes before committing
- Fix all linting errors and warnings before proceeding
- Linting includes both formatting (ruff format) and checks (ruff check)

### Makefile Usage
- Use Makefile for all development operations:
  - `make clean` - Clean environment
  - `make install` - Setup venv and install package  
  - `make test` - Run all tests
  - `make lint` - Format and lint code
  - `make dist` - Build distribution

### Testing
- Run `make test` to execute all unit tests
- All tests must pass before committing
- Keep tests simple and focused on core functionality
- Tests should be in `src/tests/` directory

## Import Conventions

### Package Imports
- **DO NOT** use relative imports like `from .module import`
- **DO** use absolute imports: `from doctor.configs.models import Config`
- **DO** use package-level imports: `from doctor import main`

### Examples
```python
# ❌ Wrong
from .models import Config
from .loader import load_config

# ✅ Correct  
from doctor.configs.models import Config
from doctor.configs.loader import load_configs
```

## Exception Handling

### Exception Chaining
- **MUST** use proper exception chaining with `from` clause
- This preserves the original traceback for debugging

```python
# ❌ Wrong
except SomeError as e:
    raise ValueError(f"Custom message: {e}")

# ✅ Correct
except SomeError as e:
    raise ValueError(f"Custom message: {e}") from e
```

## Code Quality Standards

### Linting Requirements
- All ruff checks must pass
- No remaining linting errors or warnings
- Code is automatically formatted with ruff format

### Type Safety
- Use Pydantic models for configuration validation
- Include proper type hints throughout
- Use enums for constrained choices

### Error Messages
- Provide clear, descriptive error messages
- Include relevant context (file paths, values, etc.)
- Use proper exception types (FileNotFoundError, ValueError, etc.)

## Project Structure Conventions

### Module Organization
```
src/doctor/
├── __init__.py              # Main package exports
├── cli.py                   # Command line interface
├── config/                  # Configuration management
│   ├── __init__.py         # Config package exports
│   ├── models.py           # Pydantic data models
│   └── loader.py           # Configuration loading logic
└── ...                     # Future modules
```

### File Naming
- Use snake_case for Python files
- Use descriptive module names
- Keep modules focused on single responsibility

## Documentation Standards

### Docstrings
- Use triple quotes for all docstrings
- Include brief description and parameters
- Document return values and exceptions

```python
def load_config(config_paths: Optional[List[Path]] = None) -> Config:
    """
    Load configuration with defaults fallback.
    
    Args:
        config_paths: List of user configuration file paths.
                     If None or empty, only defaults are loaded.
    
    Returns:
        Config: Validated configuration object
        
    Raises:
        FileNotFoundError: If configuration files are not found
        ValueError: If configuration is invalid
    """
```

### Comments
- Use comments sparingly, prefer self-documenting code
- Add comments for complex logic or business rules
- Update comments when code changes

## Git Conventions

### Commit Messages
- Use descriptive commit messages
- Include context about what and why
- Reference issues when applicable

### Branching
- Work on feature branches
- Use descriptive branch names
- Keep commits focused and atomic

## Configuration Management

### TOML Structure
- Use metric units (cm, mm) not imperial (inches)
- Use CSS units (rem, em, px) for web properties
- Separate configuration data (TOML) from styling implementation (CSS)

### Validation
- All configuration must pass Pydantic validation
- Use appropriate field constraints and enums
- Provide meaningful default values

## Performance Considerations

### Loading
- Load defaults once and cache
- Deep merge configurations efficiently
- Validate early and fail fast

## Security

### File Handling
- Validate file paths and existence
- Use appropriate encodings (UTF-8)
- Handle permission errors gracefully

## Future Guidelines

**TODO: Add conventions as they are established:**
- [ ] Logging standards
- [ ] Async/await patterns (when needed)
- [ ] Database integration patterns (if applicable)
- [ ] API design conventions (for Phase 2 web app)
- [ ] Frontend code standards (for Phase 2 web app)
- [ ] Testing patterns for different components
- [ ] Performance benchmarking standards
- [ ] Documentation generation automation
- [ ] Release and deployment procedures

---

**Remember**: Update this document whenever new coding conventions, patterns, or requirements are established during development. This serves as the single source of truth for project standards.
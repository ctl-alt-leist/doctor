# Doctor: Academic Document Generation from Obsidian Notes

## Project Overview

**Doctor** is a Python-based command-line tool that converts Obsidian-style markdown directories into professionally
formatted academic documents. Unlike traditional markdown processors, Doctor provides full control over document
styling, typography, and layout while maintaining LaTeX-quality mathematical typesetting.

### Core Philosophy

Doctor bridges the gap between the ease of Obsidian note-taking and the professional output quality expected in academic
work. It treats Obsidian vaults as structured document sources and provides multiple high-quality output formats with
complete stylistic control.

## Output Formats

Doctor generates three primary output formats:

### 1. PDF Generation
- **Primary use**: Print-ready academic documents, papers, theses
- **Typography**: Professional LaTeX-quality typesetting
- **Equations**: Native LaTeX rendering for mathematical expressions
- **Citations**: Full academic citation formatting and bibliography
- **Figures**: High-resolution image embedding with proper captioning

### 2. HTML Generation  
- **Primary use**: Web publication, online sharing, interactive documents
- **Typography**: CSS-controlled styling with web fonts
- **Equations**: MathJax/KaTeX rendering for mathematical expressions
- **Citations**: Hyperlinked references and bibliography
- **Figures**: Responsive image handling with web-optimized formats
- **Interactivity**: Collapsible sections, linked cross-references

### 3. Interactive Web Application
- **Primary use**: Obsidian-like editing and viewing experience
- **Live editing**: In-place content editing with real-time preview
- **WYSIWYG interface**: Type directly into rendered HTML with markdown shortcuts
- **Seamless workflow**: Edit → Preview → Export pipeline
- **Collaborative features**: Real-time collaboration capabilities (future)
- **Offline support**: Progressive Web App (PWA) functionality

## Obsidian Integration

### Directory Structure Processing
Doctor intelligently processes Obsidian vault structures:

```
Research-Vault/
├── 0. TITLE/
│   ├── 0. Title Page.md
│   └── 1. Abstract.md
├── 1. Introduction/
│   ├── overview.md
│   └── background.md
├── 2. Methods/
│   └── analysis.md
├── _figures/
│   ├── experiment-setup.png
│   └── results-chart.svg
├── _templates/
│   └── custom-styles.css
└── references.toml
```

### Obsidian Feature Support
- **Wikilinks**: `[[Internal Link]]` → proper cross-references
- **Embeds**: `![[figure.png]]` → figure insertion with captions
- **Tags**: `#important` → styling classes or index generation
- **Block references**: `^block-id` → equation numbering and referencing
- **Callouts**: `> [!note]` → styled information boxes
- **Mathematical expressions**: Full LaTeX math support in `$...$` and `$$...$$`

## Configuration System

### Hierarchical TOML Configuration
Doctor uses a sophisticated configuration hierarchy:

1. **System defaults** (built into Doctor)
2. **User global** (`~/.config/doctor/config.toml`)
3. **Project-specific** (`doctor.toml` in vault root)
4. **CLI overrides** (command-line arguments)

### Configuration Categories

#### Document Configuration (`document.toml`)
```toml
[document]
title = "Research Paper Title"
author = "Author Name"
date = "2025-01-15"
document_class = "article"  # article, book, thesis
language = "en"
abstract_enabled = true
```

#### Typography Configuration (`typography.toml`)
```toml
[typography]
# PDF-specific fonts
pdf_main_font = "Times New Roman"
pdf_math_font = "Computer Modern"
pdf_mono_font = "Source Code Pro"

# HTML-specific fonts
html_main_font = "Georgia, serif"
html_math_font = "KaTeX_Main"
html_mono_font = "Source Code Pro, monospace"

# Sizing
base_font_size = "11pt"
line_height = 1.5
margin_size = "1in"
```

#### Layout Configuration (`layout.toml`)
```toml
[layout]
# Page setup
page_size = "letter"  # a4, letter, legal
orientation = "portrait"
columns = 1
column_gap = "2em"

# Section formatting
section_numbering = true
toc_enabled = true
toc_depth = 3
page_breaks_before_chapters = true

# Header/Footer
header_enabled = true
footer_enabled = true
page_numbers = "bottom-center"
```

#### Equation Configuration (`equations.toml`)
```toml
[equations]
# LaTeX packages for PDF
latex_packages = ["amsmath", "amssymb", "physics", "braket"]

# MathJax/KaTeX for HTML
html_math_renderer = "mathjax"  # mathjax, katex
html_math_config = "TeX-MML-AM_CHTML"

# Numbering
equation_numbering = true
equation_prefix = "Eq."
```

#### Bibliography Configuration (`bibliography.toml`)
```toml
[bibliography]
enabled = true
style = "apa"  # apa, mla, chicago, nature, etc.
references_file = "references.toml"
cite_style = "author-year"  # numeric, author-year
```

#### Output Configuration (`output.toml`)
```toml
[output]
# File naming
filename_pattern = "{title}-{date}"
build_directory = ".doctor"
clean_build = false

# PDF-specific
pdf_quality = "high"
pdf_compression = true

# HTML-specific
html_standalone = true
html_embed_assets = true
html_theme = "academic"
```

## CSS Styling System

### CSS-First Design Philosophy
Doctor prioritizes CSS for styling control, even for PDF generation. This provides:

- **Unified styling** across HTML and PDF outputs
- **Web developer familiarity** with CSS syntax
- **Rapid iteration** without LaTeX compilation delays
- **Modern layout capabilities** (flexbox, grid, etc.)

### CSS Integration Methods

#### For HTML Output
Direct CSS application with full web standards support:
- External stylesheets
- Embedded styles
- CSS custom properties (variables)
- Responsive design with media queries

#### For PDF Output
CSS-to-PDF conversion using tools like WeasyPrint or Playwright:
- CSS `@page` rules for page layout
- Print-specific media queries
- CSS transforms for advanced layouts
- Custom CSS properties for template variables

### Style Template System
```
_templates/
├── base.css              # Core typography and layout
├── academic.css          # Academic paper styling
├── thesis.css            # Thesis-specific formatting
├── presentation.css      # Slide-style output
└── custom/
    ├── university-brand.css
    └── personal-theme.css
```

## LaTeX Integration Strategy

### Hybrid LaTeX Approach
Doctor uses LaTeX selectively for what it does best:

#### For PDF Generation
- **Option A**: LaTeX-only for equations, CSS for everything else
  - Generate individual equation SVGs using LaTeX
  - Embed in CSS-styled document
  - Pros: Full styling control, faster iteration
  - Cons: Complex baseline alignment

- **Option B**: Full LaTeX with CSS-inspired templates
  - Convert CSS styling to LaTeX commands
  - Use Jinja2 templates for LaTeX generation
  - Pros: Perfect equation integration
  - Cons: LaTeX debugging complexity

#### For HTML Generation
- **MathJax/KaTeX** for mathematical expressions
- Pure CSS for all document styling
- JavaScript for interactive features

### LaTeX Package Management
```toml
[latex_packages]
# Core mathematical packages
math_core = ["amsmath", "amssymb", "mathtools"]

# Physics-specific packages
physics = ["physics", "braket", "units"]

# Typography and formatting
typography = ["fontspec", "microtype", "geometry"]

# Graphics and figures
graphics = ["graphicx", "tikz", "pgfplots"]

# Bibliography
bibliography = ["biblatex", "csquotes"]
```

## Development Environment (uv-based)

### Project Structure
```
doctor/
├── pyproject.toml         # uv project configuration
├── uv.lock               # Dependency lockfile
├── Makefile              # Development shortcuts
├── ruff.toml             # Code formatting config
├── doctor.toml           # Self-documenting config
├── src/
│   └── doctor/
│       ├── __init__.py
│       ├── cli.py        # Click-based CLI
│       ├── config/       # Configuration system
│       ├── parsers/      # Markdown and Obsidian parsing
│       ├── generators/   # PDF and HTML generation
│       ├── templates/    # Default CSS and LaTeX templates
│       └── utils/        # Utility functions
├── tests/
│   ├── fixtures/         # Sample Obsidian vaults
│   ├── test_config.py
│   ├── test_parsing.py
│   └── test_generation.py
└── docs/
    ├── examples/         # Sample configurations
    └── templates/        # Template gallery
```

### Development Workflow
```bash
# Environment setup
make setup                # Create .venv with uv
make install             # Install in development mode

# Development
make dev                 # Install with dev dependencies
make lint                # Format code with ruff
make test                # Run pytest test suite

# Testing
make test-pdf            # Test PDF generation
make test-html           # Test HTML generation
make test-samples        # Process sample vaults

# Building
make build               # Build distribution
make clean               # Clean build artifacts
```

## Processing Architecture: Separation of Powers

The Doctor processing pipeline employs strict separation of powers to ensure modularity, testability, and
maintainability. Each processing stage operates independently with well-defined inputs and outputs.

### Core Processing Modules

#### 1. Content Ingestion (`doctor.ingest`)
**Responsibility**: Read and parse markdown files, inventory vault contents
- **Input**: Vault directory path, file discovery rules
- **Processing**: 
  - Recursive file discovery with exclusion patterns
  - Markdown parsing and metadata extraction
  - Asset discovery (figures, attachments, etc.)
  - Link and reference extraction
- **Output**: Content inventory object with parsed markdown, metadata, and asset catalog
- **Interface**: `ContentInventory = ingest_vault(vault_path: Path) -> ContentInventory`

#### 2. Table of Contents Generation (`doctor.toc`)
**Responsibility**: Analyze document structure and generate table of contents
- **Input**: Content inventory with heading hierarchy
- **Processing**:
  - Extract heading structure from all documents
  - Build hierarchical document outline
  - Generate section numbering schemes
  - Create navigation links and page references
- **Output**: TOC data structure with formatting instructions
- **Interface**: `TOCStructure = build_toc(content: ContentInventory) -> TOCStructure`

#### 3. Bibliography Management (`doctor.bibliography`)
**Responsibility**: Process citations and generate bibliography
- **Input**: Content inventory with citation references, bibliography files
- **Processing**:
  - Parse TOML reference files and citation databases
  - Match in-text citations to bibliography entries
  - Apply citation styles (APA, MLA, Chicago, etc.)
  - Generate formatted bibliography entries
- **Output**: Bibliography object with formatted citations and reference list
- **Interface**: `Bibliography = process_bibliography(content: ContentInventory, style: str) -> Bibliography`

#### 4. Cross-Reference Tracking (`doctor.references`)
**Responsibility**: Track and resolve all internal references (figures, equations, sections)
- **Input**: Content inventory with embedded references
- **Processing**:
  - Identify figure references (`![[figure.png]]`, `[@fig:experiment]`)
  - Track equation references (`[@eq:schrodinger]`)
  - Map section cross-references (`[@sec:methodology]`)
  - Generate automatic numbering for figures, equations, tables
  - Resolve forward and backward references
- **Output**: Reference map with numbering and link targets
- **Interface**: `ReferenceMap = track_references(content: ContentInventory) -> ReferenceMap`

#### 5. Configuration Management (`doctor.configs`)
**Responsibility**: Load, validate, and merge all configuration sources
- **Input**: Configuration file paths, CLI overrides
- **Processing**:
  - Load hierarchical configuration (defaults → user → project → CLI)
  - Validate configuration schemas with Pydantic
  - Resolve configuration inheritance and overrides
  - Generate derived configurations (CSS variables, LaTeX commands)
- **Output**: Complete configuration object for document generation
- **Interface**: `DocumentConfig = load_configs(config_paths: List[Path]) -> DocumentConfig`

#### 6+. Output Generation Modules (`doctor.generators.*`)
**Philosophy**: Output generation will employ the same separation of powers as modules 1-5, with each output format
having multiple specialized modules rather than monolithic generators.

**Expected Separation** (details to be determined during implementation):
- **Document Structure Assembly**: Combining processed content into document hierarchy
- **Asset Processing**: Image optimization, figure placement, file embedding  
- **Style Application**: CSS/LaTeX styling, theme application, typography
- **Format-Specific Rendering**: PDF compilation, HTML generation, app bundling
- **Post-Processing**: Optimization, validation, metadata embedding
- **Output Finalization**: File writing, cleanup, result reporting

**Anticipated Module Structure**:
```python
# These interfaces will be refined during implementation
doctor.generators.structure     # Document assembly and layout
doctor.generators.assets       # Asset processing and optimization  
doctor.generators.styling      # Style and theme application
doctor.generators.pdf          # PDF-specific rendering pipeline
doctor.generators.html         # HTML-specific rendering pipeline
doctor.generators.app          # Interactive app generation pipeline
doctor.generators.finalize     # Output finalization and cleanup
```

**Note**: The exact separation of powers for output generation modules will be determined through implementation
experience and requirements discovery. The principle of single responsibility per module will be maintained.

### Processing Pipeline Flow

```python
# Conceptual processing pipeline
def process_vault(vault_path: Path, output_path: Path, config_overrides: Dict) -> None:
    # Stage 1: Content ingestion
    content = ingest.ingest_vault(vault_path)
    
    # Stage 2: Structure analysis  
    toc = toc.build_toc(content)
    
    # Stage 3: Bibliography processing
    bibliography = bibliography.process_bibliography(content, config.citation_style)
    
    # Stage 4: Reference resolution
    references = references.track_references(content)
    
    # Stage 5: Configuration loading
    config = config.load_configs(config_paths, config_overrides)
    
    # Stage 6: Output generation
    for output_format in config.output_formats:
        generator = generators.get_generator(output_format)
        generator.generate_output(content, toc, bibliography, references, config, output_path)
```

### Module Independence and Testing

Each processing module operates independently, enabling:

- **Unit Testing**: Each module tested in isolation with mock data
- **Pipeline Testing**: Integration tests with controlled intermediate states  
- **Debugging**: Clear failure points and state inspection
- **Caching**: Expensive operations cached at module boundaries
- **Parallel Processing**: Independent modules can run concurrently where applicable

### Data Contracts

Clear interfaces between modules prevent tight coupling:

```python
# Example data contracts
@dataclass
class ContentInventory:
    files: List[MarkdownFile]
    assets: List[AssetFile]
    metadata: VaultMetadata
    links: List[InternalLink]

@dataclass  
class TOCStructure:
    entries: List[TOCEntry]
    numbering_scheme: NumberingScheme
    depth: int

@dataclass
class ReferenceMap:
    figures: Dict[str, FigureRef]
    equations: Dict[str, EquationRef]  
    sections: Dict[str, SectionRef]
    numbering: AutoNumbering
```

This separation of powers ensures that each processing stage has a single, well-defined responsibility, making the
system more maintainable, testable, and extensible.

### Code Quality Standards
- **Type hints**: Full type annotation with mypy checking
- **Code formatting**: Ruff with 120-character line length
- **Testing**: pytest with >90% coverage requirement
- **Documentation**: Comprehensive docstrings and examples
- **Import style**: Absolute imports, specific imports preferred

## Command-Line Interface

### Primary Commands
```bash
# Basic conversion
doctor convert /path/to/vault --output paper.pdf
doctor convert /path/to/vault --output site.html

# With configuration
doctor convert vault/ --config academic.toml --style thesis.css

# Multiple outputs
doctor convert vault/ --pdf paper.pdf --html site.html

# Interactive application modes
doctor app vault/         # Launch web-based editing application
doctor serve vault/       # Serve vault as live-editing website
doctor preview vault/     # Read-only live preview server

# Development and validation
doctor validate vault/    # Check vault structure and refs
doctor init              # Create example configurations
doctor template --type academic  # Generate project templates
```

### Advanced Options
```bash
# Configuration management
doctor config list                    # Show current config hierarchy
doctor config validate academic.toml # Validate config file
doctor config template --style thesis # Generate config template

# Debugging and development
doctor convert vault/ --verbose       # Detailed logging
doctor convert vault/ --dry-run       # Show what would be done
doctor convert vault/ --keep-build    # Preserve intermediate files
```

## Plugin and Extension System

### Template System
Users can create custom templates for:
- CSS styling themes
- LaTeX class files
- HTML layouts
- Citation styles

### Processor Plugins
Extensible processors for:
- Custom markdown syntax
- Specialized mathematical notation
- Domain-specific formatting (code, chemistry, etc.)
- Output format plugins (EPUB, Word, etc.)

## Error Handling and Debugging

### Comprehensive Logging
- **Info level**: Processing progress and file discovery
- **Debug level**: Detailed parsing and conversion steps
- **Error level**: Clear error messages with fix suggestions

### Validation System
- **Pre-flight checks**: Vault structure validation
- **Reference validation**: Broken links and missing figures
- **Configuration validation**: TOML schema validation
- **Output validation**: PDF/HTML generation success

### Recovery and Fallbacks
- **Graceful degradation**: Continue processing despite individual file errors
- **Partial outputs**: Generate what's possible, report what failed
- **Backup preservation**: Keep intermediate files for debugging

## Performance and Scalability

### Efficient Processing
- **Incremental builds**: Only regenerate changed content
- **Parallel processing**: Multi-threaded file processing
- **Caching system**: Cache parsed markdown and generated assets
- **Memory management**: Stream processing for large vaults

### Build Optimization
- **Asset optimization**: Compress images, minify CSS
- **Smart dependencies**: Track file dependencies for minimal rebuilds
- **Output caching**: Cache expensive operations (LaTeX compilation)

## Development Approaches and Repository Structure

### Git Repository Organization
The Doctor project employs a structured branching strategy to explore different technical approaches:

#### Branch Structure
```
├── main                           # Stable releases, project essentials only
├── dev                           # Active development integration branch
├── feature/latex-backend         # Pure LaTeX approach
└── feature/css-html-backend      # CSS/HTML-first approach
```

#### Branch Purposes

**`main` Branch**
- Minimal, stable project configuration
- Essential files: `pyproject.toml`, `README.md`, `Makefile`, `.gitignore`
- Documentation and specifications
- Release tags and stable versions

**`dev` Branch** 
- Integration branch for active development
- Full development environment setup
- Testing infrastructure and sample data
- Experimental features and integration testing

**`feature/latex-backend` Branch**
- Pure LaTeX approach using PyLaTeX or similar
- Focus on LaTeX-quality PDF output
- Traditional academic document workflow
- Full LaTeX ecosystem integration

**`feature/css-html-backend` Branch**
- CSS-first styling with HTML as primary format
- JavaScript-based interactive features
- Modern web technologies (CSS Grid, Flexbox)
- HTML→PDF conversion for print output

### Interactive Web Application Architecture

#### Core Technology Stack
- **Frontend**: Modern JavaScript (ES6+) with HTML5 and CSS3
- **Editor**: CodeMirror or Monaco Editor with markdown syntax highlighting
- **Math Rendering**: MathJax 3.x with LaTeX input support
- **Real-time Preview**: Live updating with debounced rendering
- **Offline Support**: Service Workers and IndexedDB for local storage

#### Application Features

**Live Editing Interface**
```javascript
// Conceptual architecture
class DoctorApp {
  constructor(vaultPath) {
    this.editor = new MarkdownEditor();
    this.preview = new LivePreview();
    this.fileManager = new VaultManager(vaultPath);
  }
  
  // Real-time editing with math support
  onEdit(content) {
    this.preview.updateContent(content);
    this.mathRenderer.renderMath();
  }
}
```

**WYSIWYG Capabilities**
- **Inline editing**: Click-to-edit functionality in preview pane
- **Math editing**: Visual equation editor with LaTeX input
- **Link management**: Drag-and-drop internal linking
- **Image handling**: Paste and upload with automatic optimization
- **Table editing**: Spreadsheet-like table manipulation

**Export Integration**
- **One-click export**: Generate PDF/HTML from current state
- **Background processing**: Non-blocking document generation
- **Progress feedback**: Real-time export status updates
- **Error handling**: Visual feedback for export issues

#### Progressive Web App Features
```json
// manifest.json concept
{
  "name": "Doctor Academic Editor",
  "short_name": "Doctor",
  "description": "Academic document creation and editing",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#2c3e50",
  "background_color": "#ecf0f1",
  "icons": [...],
  "offline_fallback": "/offline.html"
}
```

#### Technical Implementation Strategy

**Hybrid Architecture**
- **Server component**: Python backend for document processing
- **Client component**: JavaScript frontend for editing experience
- **API layer**: RESTful API for file operations and export
- **WebSocket integration**: Real-time collaboration (future feature)

**File System Integration**
```python
# Python backend API endpoints
@app.route('/api/vault/<path:file_path>')
def get_file(file_path):
    """Serve markdown files with metadata"""
    
@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Generate PDF from current vault state"""
    
@app.route('/api/preview/live')
def live_preview():
    """WebSocket for real-time preview updates"""
```

### Implementation Roadmap

#### Phase 1: Core Infrastructure (feature branches)
- Set up parallel development tracks for LaTeX vs CSS approaches
- Implement basic markdown parsing and file discovery
- Create configuration system foundation

#### Phase 2: Output Generation
- **LaTeX branch**: Implement PyLaTeX pipeline with equation support  
- **CSS branch**: Implement HTML generation with CSS styling
- Comparative evaluation of both approaches

#### Phase 3: Interactive Application
- Build web-based editing interface
- Integrate chosen backend approach
- Implement real-time preview and editing

#### Phase 4: Advanced Features
- Export optimization and multi-format support
- Collaboration features and conflict resolution
- Plugin system and template marketplace

## Recent Implementation: Professional Academic Formatting

### CSS-First Professional Document Features (Completed)

Recent development has successfully implemented professional academic document formatting using a CSS-first approach:

#### Professional Title Page
- **Clean Layout**: Centered title, author, date with academic typography
- **Configurable**: Metadata from `doctor.toml` configuration
- **Print-Ready**: Proper page breaks and professional spacing

#### Dynamic Document Structure
- **Front Matter Detection**: Automatic identification of prefaces, overviews, abstracts
- **Page Break Logic**: Configurable page breaks between major document parts
- **Multi-page HTML**: Professional navigation with organized table of contents
- **Category Organization**: Front matter, main content, and appendices automatically categorized

#### Advanced Features
- **Figure Integration**: Automatic figure copying and path resolution
- **Academic Typography**: Times New Roman, justified text, proper heading hierarchy
- **Dual PDF Generation**: WeasyPrint primary with Playwright fallback for cross-platform compatibility
- **Configuration-Driven**: Document structure defined in `doctor.toml` rather than hardcoded

#### Technical Approach
- **Dynamic Templates**: Jinja2 templates with helper functions for document structure detection
- **No Hardcoding**: Section names and structure determined automatically from directory organization
- **Cross-Platform**: Robust figure copying and PDF generation across different environments
- **Professional Output**: LaTeX-quality formatting using modern CSS and HTML-to-PDF conversion

This implementation demonstrates the viability of the CSS-first approach for producing professional academic documents
while maintaining flexibility and modern development practices.

---

This specification provides the foundation for rebuilding Doctor as a comprehensive academic document ecosystem that
spans from simple note-taking to professional publication, while maintaining the flexibility to explore different
technical approaches through structured development branches.

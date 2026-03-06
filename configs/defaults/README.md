# Doctor Default Configuration

This directory contains the default configuration system for Doctor academic document generation.

## Architecture

**CSS-First Approach**: We use CSS/HTML for document styling and layout, with LaTeX **only** for mathematical notation
rendering. No LaTeX document classes or typography packages.

**Configuration Philosophy**:
- **TOML files** = Configuration data (what fonts to use, which citation style, document metadata)
- **CSS files** = Styling implementation (how those choices are rendered)
- **No duplication** = Each setting lives in exactly one place

## TOML Configuration Files

### Core Configuration
- **`document.toml`** - Document metadata, type (article/book/thesis), structure settings
- **`typography.toml`** - Font families, size scales, spacing preferences
- **`layout.toml`** - Page geometry, margins, responsive breakpoints  
- **`math.toml`** - Math renderer settings, LaTeX math packages, equation formatting
- **`bibliography.toml`** - Citation styles, bibliography backends, reference formatting
- **`figures.toml`** - Image formats, figure placement, table settings
- **`output.toml`** - Output formats (HTML/PDF), compilation settings

### Units and Measurements
- **Print/PDF**: `cm`, `mm` (metric only, no inches)
- **Web/HTML**: `rem`, `em`, `px` for responsive design
- **Simple approach**: Standardized on essential CSS units

## CSS Implementation

### Generated Custom Properties
TOML configs generate CSS custom properties:
```css
:root {
  /* From typography.toml */
  --font-serif: 'Crimson Text', 'Georgia', serif;
  --size-normal: 1rem;
  
  /* From layout.toml */
  --page-margin-top: 2.5cm;
  --section-spacing: 2rem;
  
  /* From math.toml */
  --equation-spacing: 1rem;
}
```

### Modular Stylesheets
- **`main.css`** - Master file with CSS custom properties and imports
- **`typography.css`** - Text formatting, font hierarchy
- **`layout.css`** - Page structure, responsive grid
- **`math.css`** - Mathematical notation styling
- **`bibliography.css`** - Citations and references
- **`figures.css`** - Images, tables, captions
- **`print.css`** - Print/PDF optimizations

### Document Types
Document-specific CSS classes from `document.toml`:
- `.document-type-article` - Compact journal formatting
- `.document-type-book` - Book layout with chapters
- `.document-type-thesis` - Formal academic requirements

## Math Handling

**LaTeX for Math Only**: Mathematical expressions use LaTeX syntax but are rendered to HTML via MathJax/KaTeX for web,
and to SVG for PDF inclusion.

**No LaTeX Backend**: Document layout, typography, and styling are purely CSS/HTML based.

## Workflow

1. **Configuration**: User edits TOML files or uses presets
2. **Processing**: Doctor tool reads TOML configs
3. **Generation**: 
   - Generates CSS custom properties from TOML values
   - Processes markdown with math expressions
   - Renders HTML with CSS styling
   - Converts to PDF via CSS-to-PDF engine (WeasyPrint/Playwright)

## Document Type Presets

Each document type has preset configurations:

**Article**: Compact, single/double column, citation-focused
```toml
[document.presets.article]
type = "article"
numbering_depth = 2
include_toc = false
```

**Book**: Chapters, TOC, binding margins
```toml
[document.presets.book] 
type = "book"
chapters.enabled = true
two_sided.enabled = true
```

**Thesis**: Formal requirements, committee pages, strict formatting
```toml
[document.presets.thesis]
type = "thesis" 
margins = { top = "3.5cm", inner = "3.5cm" }
```

This approach provides LaTeX-quality output through modern CSS while maintaining flexibility for multiple output formats
and responsive design.

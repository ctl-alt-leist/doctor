# Claude Conversation History - Doctor Project

> **Note**: This document is for reference only. We don't need to relive this history - it's captured here to understand the project evolution and key decisions made.

## Project Evolution Summary

### Initial Concept: TeXit
- **Goal**: Convert Obsidian markdown directories to LaTeX/PDF documents
- **Approach**: Python CLI tool with PyLaTeX backend
- **Key Features**: Mathematical equations, citations, figures, configurable styling

### Technical Implementation (First Attempt)
1. **Project Setup**: Used `uv` for dependency management, Click for CLI
2. **Configuration System**: Hierarchical TOML configs (defaults → user → project → CLI)
3. **File Discovery**: Recursive markdown file discovery with exclusion rules
4. **Processing Pipeline**: Markdown → HTML → LaTeX → PDF using PyLaTeX
5. **Math Handling**: Custom markdown extensions to protect LaTeX expressions
6. **Unicode Support**: Greek letter conversion for LaTeX compatibility

### Critical Issues Discovered
- **HTML Artifacts**: Raw HTML tags appearing in PDF output
- **Math Placeholder Failures**: Protected expressions not being restored
- **Table of Contents Problems**: Generic "TITLE" entries instead of actual content
- **Document Structure Issues**: Improper section hierarchy generation
- **Complex Debugging**: LaTeX compilation errors difficult to trace

### Philosophical Shift
- **Recognition**: LaTeX is powerful but complex for document layout
- **New Approach**: Use LaTeX only for equations, handle layout with CSS/HTML
- **Expanded Vision**: Multiple output formats (PDF, HTML, interactive web app)

### Project Rebranding: Doctor
- **Broader Scope**: Academic document ecosystem, not just PDF generation
- **Three Output Formats**:
  1. PDF for print/academic submission
  2. HTML for web publication
  3. Interactive web application for Obsidian-like editing

### Architecture Decisions
- **CSS-First Styling**: Maximum control over typography and layout
- **Hybrid LaTeX**: Use LaTeX only for mathematical expressions
- **Modern Web Technologies**: JavaScript frontend, Python backend API
- **Progressive Web App**: Offline editing capabilities

### Repository Structure Plan
```
main (project essentials only)
├── dev (full development environment)  
├── feature/latex-backend (pure LaTeX approach)
└── feature/css-html-backend (CSS/HTML-first approach)
```

## Key Technical Lessons Learned

### What Worked Well
- **uv dependency management**: Fast, reliable package handling
- **TOML configuration**: Hierarchical config system was elegant
- **Click CLI**: Professional command-line interface
- **Pydantic models**: Excellent config validation and type safety
- **File discovery**: Robust directory traversal with exclusions

### What Proved Challenging
- **Markdown → HTML → LaTeX Pipeline**: Too many conversion steps introduced artifacts
- **PyLaTeX Integration**: Complex debugging when LaTeX compilation failed
- **Math Expression Protection**: Placeholder system was fragile
- **Unicode Handling**: Required extensive manual conversion mappings
- **Document Structure Mapping**: Directory hierarchy to LaTeX sections was error-prone

### Critical Insights
1. **LaTeX Complexity**: Excellent for equations, overkill for document layout
2. **Web Technologies**: More flexible and debuggable than LaTeX for styling
3. **Separation of Concerns**: Math rendering vs document layout should be separate
4. **User Experience**: Interactive editing is as important as final output quality

## Additional Features to Consider

### Academic Workflow Enhancements
- **Citation Management**: Import from Zotero, Mendeley, EndNote
- **Reference Validation**: Check DOI links, broken citations
- **Collaborative Commenting**: Track changes and reviewer feedback
- **Version Control Integration**: Git-based document history
- **Academic Templates**: Pre-built styles for journals, conferences, theses

### Content Management
- **Asset Pipeline**: Image optimization and format conversion
- **Cross-Reference System**: Automatic figure, table, equation numbering
- **Index Generation**: Automatic keyword indexing and glossaries
- **Multi-language Support**: International typography and RTL text

### Export and Integration
- **Multi-format Export**: EPUB, DOCX, XML for journal submission
- **Journal-Specific Formatting**: IEEE, ACM, Nature style templates
- **Submission Helpers**: Generate cover letters, supplement materials
- **Archive Generation**: Complete submission packages with assets

### Interactive Application Features
- **Real-time Collaboration**: Multiple users editing simultaneously
- **Comment System**: Inline comments and suggestions
- **Research Mode**: Integration with external databases and APIs
- **Presentation Mode**: Slide generation from outline structure
- **Mobile Editing**: Responsive design for tablet/phone editing

### Power User Features
- **Plugin System**: Custom processors for domain-specific notation
- **Macro Language**: User-defined shortcuts and automation
- **API Access**: Programmatic document generation
- **Batch Processing**: Convert multiple vaults simultaneously
- **Custom Themes**: Community marketplace for templates and styles

## Project Status
- **Current State**: Specification complete, ready for implementation
- **Next Steps**: Set up clean repository structure and begin development
- **Approach**: Parallel development tracks to evaluate different technical strategies
- **Timeline**: Iterative development with regular evaluation of approaches

This history captures the journey from a simple markdown-to-PDF converter to a comprehensive academic document ecosystem vision.
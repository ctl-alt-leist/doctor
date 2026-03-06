## Doctor Project: Phase Summary

### Phase 1: Clean Web + PDF Generation
**Goal**: Reliable, professional document output from Obsidian vaults

**What this accomplishes**:
- CSS-first styling system with complete typography control
- Dual-output pipeline: HTML for web, PDF for print/submission
- Configuration-driven formatting (no inline styling decisions)
- Professional academic document quality matching LaTeX standards

**Technical approach**:
- Separation of powers architecture: ingest → structure → references → bibliography → output
- WeasyPrint or Playwright for CSS-to-PDF conversion
- MathJax for HTML math, LaTeX compilation for PDF math (hybrid approach)
- TOML configuration hierarchy: defaults → user → project → CLI overrides

**Success metric**: You can write a paper in clean markdown and get publication-ready output without touching LaTeX.

### Phase 2: Obsidian-like Editing App
**Goal**: Modern editing environment that understands your document pipeline

**What this accomplishes**:
- Real-time preview using your actual CSS styles (not generic markdown)
- Live cross-reference updating (figures, equations, citations auto-renumber)
- Integrated bibliography management with visual citation insertion
- File management that respects your vault organization

**Technical approach**:
- Python backend API serving the document processing pipeline
- Modern JavaScript frontend with live preview
- WebSocket connections for real-time updates
- Progressive Web App capabilities for offline editing

**Success metric**: You prefer writing in this app over Obsidian because it shows you exactly what your final document
will look like.

### Phase 3: Redefining Markdown Authoring
**Goal**: Clean, semantic syntax that prioritizes readability over LaTeX compatibility

**What this accomplishes**:
- Mathematical notation that reads naturally: `{ b } / { c }` instead of `\frac{b}{c}`
- First-class citations with auto-completion and metadata display
- Semantic cross-references that understand document structure
- Physics-aware notation without package management hell

**Technical approach**:
- Custom markdown parser with semantic mathematical expressions
- AST-based math representation that can render to multiple backends
- Configuration-driven notation preferences (Dirac vs Schrödinger, etc.)
- Live validation of references and citations

**Success metric**: Your source documents are readable by non-LaTeX users but still produce professional mathematical
typesetting.

### Phase 4: Beyond LaTeX (Math Revolution)
**Goal**: Replace LaTeX with modern, semantic mathematical typesetting

**What this accomplishes**:
- Semantic math notation that separates meaning from presentation
- Interactive equations that can be manipulated or linked to computations
- Physics-native support for units, tensors, quantum notation
- Modern layout capabilities using CSS Grid/Flexbox paradigms

**Technical approach**:
- Mathematical expression AST with multiple rendering backends
- Custom typography engine built on modern web standards
- Plugin system for domain-specific notation (quantum mechanics, field theory)
- Integration with computational tools (SymPy, Mathematica, etc.)

**Success metric**: You never need to think about LaTeX packages or formatting commands - you just write mathematics
naturally.

### Rust Migration Consideration

**When to consider Rust**:
- Phase 2/3 transition: When performance becomes critical for real-time editing
- Phase 4: When building the custom math typesetting engine
- Cross-platform distribution: Rust's zero-dependency binaries ideal for user installation

**Rust advantages for this project**:
- **Performance**: File watching, parsing, and rendering can be CPU-intensive
- **Memory safety**: Critical when processing user documents
- **Concurrency**: Excellent for parallel document processing
- **Distribution**: Single binary deployment without Python environment setup
- **WebAssembly**: Could enable browser-based document processing

**Migration strategy**:
- Start with performance-critical components (parser, file watcher)
- Gradually replace Python modules with Rust equivalents
- Maintain Python API compatibility during transition
- Eventually: pure Rust backend with Python bindings for compatibility

The Python prototype gives us rapid iteration and proof-of-concept, while Rust provides the foundation for a
production-quality tool that other academics will actually install and use reliably.

# Footnotes Implementation Plan

## Current Problem
Obsidian-style footnotes are not being properly processed and rendered:
- Raw footnote references (`[^1]`, `[^2]`) appear in PDF output instead of proper footnote numbers
- Footnote definitions (`[^1]: The history throughout...`) are showing up as raw text in the document
- No footnote rendering in HTML output
- Missing proper footnote formatting and placement

## Obsidian Footnote Syntax
```markdown
This is text with a footnote[^1] and another footnote[^2].

[^1]: The history throughout this section is probably full of mistakes, so please review this and come back to it.

[^2]: Let's work this calculation out.
```

## Implementation Plan

### Phase 1: Parsing and Detection
**Location**: `src/doctor/ingest/` (markdown parsing pipeline)

1. **Footnote Reference Detection**
   - Scan for `[^identifier]` patterns in text content
   - Extract footnote identifiers and positions
   - Replace with numbered placeholders during parsing

2. **Footnote Definition Extraction**
   - Find footnote definitions: `[^identifier]: content`
   - Extract to separate footnote collection
   - Remove from main document content during parsing
   - Store mapping of identifier → content

3. **Cross-Reference Validation**
   - Ensure all footnote references have corresponding definitions
   - Warn about orphaned references or definitions
   - Auto-number footnotes in order of appearance

### Phase 2: Data Structure Updates
**Location**: `src/doctor/ingest/assembly.py`

Update `AssembledDocument` to include:
```python
@dataclass
class FootnoteReference:
    identifier: str
    number: int
    position: int  # Character position in text
    
@dataclass
class FootnoteDefinition:
    identifier: str
    number: int
    content: str
    
class AssembledDocument:
    # ... existing fields ...
    footnote_references: List[FootnoteReference]
    footnote_definitions: List[FootnoteDefinition]
```

### Phase 3: HTML Implementation
**Location**: `src/doctor/generators/html.py`

**Approach: Tooltip/Modal System**
1. **In-text rendering**:
   - Replace `[^1]` with `<sup><a href="#fn1" class="footnote-ref" data-footnote="1">1</a></sup>`
   - Add hover tooltips with footnote content preview
   - Click opens modal/popup with full footnote content

2. **CSS Styling**:
   - Style footnote references as superscript links
   - Implement tooltip/modal CSS
   - Responsive design for mobile footnote display

3. **JavaScript Enhancement**:
   - Add footnote modal functionality
   - Keyboard navigation (Esc to close)
   - Smooth scrolling to footnote sections

4. **Fallback Footer Section**:
   - Include traditional footnotes section at document end
   - For users with JavaScript disabled
   - SEO and accessibility compliance

### Phase 4: PDF Implementation  
**Location**: `src/doctor/generators/pdf.py`

**Approach: Traditional Page-Bottom Footnotes**
1. **CSS `@page` Rules**:
   ```css
   @page {
       @footnotes {
           border-top: 1px solid black;
           margin-top: 1em;
           padding-top: 0.5em;
       }
   }
   
   .footnote-call {
       float: footnote;
       font-size: 0.8em;
   }
   ```

2. **HTML Structure for PDF**:
   - Convert footnote references to `<span class="footnote-call">content</span>`
   - Use CSS `float: footnote` to position at page bottom
   - Automatic numbering via CSS counters

3. **WeasyPrint/Playwright Compatibility**:
   - Test footnote support in both PDF engines
   - Implement fallback if native footnote support is limited
   - Manual page-break and footnote placement if needed

### Phase 5: Configuration Options
**Location**: `src/doctor/configs/models.py`

Add footnote configuration:
```toml
[footnotes]
enabled = true
style = "numeric"  # numeric, alphabetic, roman
position = "page-bottom"  # page-bottom, document-end, chapter-end
numbering = "restart-page"  # restart-page, restart-chapter, continuous
separator = "horizontal-line"  # horizontal-line, spacing, custom

[footnotes.html]
display_mode = "tooltip"  # tooltip, modal, inline, traditional
show_return_links = true
preview_length = 100  # chars in tooltip preview

[footnotes.pdf] 
font_size = "0.8em"
line_spacing = 1.2
margin_top = "1em"
separator_style = "line"  # line, space, custom
```

### Phase 6: Testing and Edge Cases
**Location**: `src/tests/`

1. **Unit Tests**:
   - Footnote parsing accuracy
   - Cross-reference resolution
   - Numbering schemes
   - Configuration handling

2. **Integration Tests**:
   - Multi-file footnote numbering
   - Page break behavior in PDF
   - HTML JavaScript functionality
   - Mobile responsive behavior

3. **Edge Cases**:
   - Footnotes in tables/figures
   - Nested footnotes
   - Footnotes in math expressions
   - Very long footnotes
   - Missing footnote definitions
   - Duplicate footnote identifiers

### Phase 7: Documentation Updates
**Location**: `docs/`, `README.md`

1. **User Documentation**:
   - Footnote syntax examples
   - Configuration options
   - Best practices for academic footnotes
   - Troubleshooting common issues

2. **Developer Documentation**:
   - Footnote processing pipeline
   - Adding new footnote styles
   - Testing footnote implementations

## Implementation Priority
1. **High Priority**: Basic parsing and PDF page-bottom footnotes
2. **Medium Priority**: HTML tooltip system and configuration
3. **Low Priority**: Advanced styling options and JavaScript enhancements

## Files to Modify
```
src/doctor/ingest/
  ├── markdown.py        # Add footnote parsing
  └── assembly.py        # Update data structures

src/doctor/generators/
  ├── html.py           # HTML footnote rendering
  ├── pdf.py            # PDF footnote CSS
  └── templates/
      ├── footnote.html  # HTML footnote templates
      └── footnote.css   # Footnote styling

src/doctor/configs/
  └── models.py         # Footnote configuration

src/tests/
  ├── test_footnotes.py # Footnote-specific tests
  └── fixtures/
      └── footnote-samples/ # Test documents with footnotes
```

## Technical Considerations
- **Performance**: Large documents with many footnotes
- **Accessibility**: Screen reader compatibility
- **Cross-references**: Integration with existing reference system
- **Markdown Compatibility**: Standard footnote syntax vs Obsidian extensions
- **Multi-format**: Consistent behavior across HTML/PDF outputs
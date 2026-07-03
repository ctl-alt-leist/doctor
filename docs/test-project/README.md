# Test Project

A fixture project for exercising the doctor compiler end to end. It is compiled
in tests and during manual verification; it is **not** part of any real notebook.

`README.md` is deliberately ignored by discovery — it is project documentation,
not manuscript content — so nothing here appears in the compiled PDF.

## Layout

```
doctor.toml               compilation + document settings
references.toml           bibliography entries
_figures/  _tables/       assets (underscore-ignored by discovery)
i. Preface.md             front matter (lowercase-roman prefix)
I. Foundations/           Part (uppercase-Roman directory)
  1. Introduction/        chapter (arabic-numbered directory)
  2. Quantum Field Theory/
II. Frontiers/            Part
  3. Black Holes/         chapter
    3. Toy Models/        sub-chapter (arabic nested in a chapter)
A. Mathematical Reference/  appendix (single-letter directory)
```

## What it exercises

- **Front matter** — `i. Preface.md` renders ahead of the body, unnumbered.
- **Part dividers** — each Roman-numbered directory opens a full-page divider.
- **Chapter title pages** — each numbered directory opens with a title page from
  its cleaned name (`3. Black Holes` → "Black Holes").
- **Sub-chapters** — an arabic directory nested inside a chapter gets an inline
  heading and bumps its files' headings one extra level.
- **Appendices** — a single-letter directory is title-paged and lettered (A, …).
- **Heading-level bump** — a file's `#` renders at the depth implied by its
  place in the tree; Parts do not add a level.
- **Math, citations, figures, cross-references** across the content files.

## Building

```bash
uv run doc docs/test-project --format pdf
uv run doc docs/test-project --format html
```

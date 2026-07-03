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
1. Introduction/          chapter (arabic-numbered directory)
2. Quantum Field Theory/
3. Black Holes/
```

## What it exercises

- **Chapter title pages** — each numbered directory opens with a title page
  taken from its cleaned name (`3. Black Holes` → "Black Holes").
- **Heading-level bump** — a chapter file's `#` renders one level deeper because
  the file sits inside a chapter directory.
- **Math, citations, figures, cross-references** across the chapter files.

## Building

```bash
uv run doc docs/test-project --format pdf
uv run doc docs/test-project --format html
```

# Doctor

Academic document generation from Obsidian notes. Doctor compiles LaTeX-heavy markdown documents into PDFs using a CSS/HTML backend approach.

## Installation

Requires Python 3.12+.

```bash
git clone https://github.com/ctl-alt-leist/doctor.git
cd doctor
make install
```

## Development

This project uses [uv](https://docs.astral.sh/uv/) for Python project management and [ruff](https://docs.astral.sh/ruff/) for linting.

```bash
make setup     # Create venv and sync dependencies
make lint      # Format and lint code
make test      # Run tests
make clean     # Remove generated files
```

---

*Claude Code was used in the development of this project.*

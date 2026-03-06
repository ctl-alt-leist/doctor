SRC_PATH = src/

.PHONY: setup install lint test build clean reset

# Development setup
setup:
	uv venv
	uv sync --extra dev

install: setup
	uv run pre-commit install

# Code quality
lint:
	uv run ruff format $(SRC_PATH)
	uv run ruff check --fix --unsafe-fixes $(SRC_PATH)

test:
	uv run pytest $(SRC_PATH)

# Build
build:
	uv build

# Cleanup
clean:
	rm -rf .venv dist/ build/
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true

reset: clean setup install

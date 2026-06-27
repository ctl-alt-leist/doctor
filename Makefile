SRC_PATH = src/
DOCTOR_HOME ?= $(HOME)/.config/doctor

.PHONY: setup install install-app uninstall-app lint test build clean reset

# Development setup
setup:
	uv venv
	uv sync --extra dev

install: setup
	uv run pre-commit install

# System-wide install: put `doc` into a bin dir already on PATH and seed default
# configs into ~/.config/doctor. Auto-picks the first writable standard bin dir;
# override with `make install-app DOC_BIN_DIR=/some/bin`.
install-app:
	@bindir="$(DOC_BIN_DIR)"; \
	if [ -z "$$bindir" ]; then \
	  for d in /opt/homebrew/bin /usr/local/bin "$(HOME)/.local/bin"; do \
	    if [ -d "$$d" ] && [ -w "$$d" ]; then bindir="$$d"; break; fi; \
	  done; \
	fi; \
	echo "Installing 'doc' into $$bindir"; \
	UV_TOOL_BIN_DIR="$$bindir" uv tool install --force --reinstall --no-cache . ; \
	mkdir -p "$(DOCTOR_HOME)/defaults"; \
	cp -R configs/defaults/. "$(DOCTOR_HOME)/defaults/"; \
	echo "Provisioning the Chromium build for PDF output..."; \
	"$$(uv tool dir)/doctor/bin/python" -m playwright install chromium; \
	echo ""; \
	echo "Installed 'doc' -> $$bindir/doc and seeded defaults into $(DOCTOR_HOME)/defaults"

# Remove the `doc` executable (uv tool plus any stray copies left in standard bins).
# Default configs in ~/.config/doctor are left in place.
uninstall-app:
	-uv tool uninstall doctor
	@for d in /opt/homebrew/bin /usr/local/bin "$(HOME)/.local/bin" $(DOC_BIN_DIR); do \
	  if [ -e "$$d/doc" ] || [ -L "$$d/doc" ]; then rm -f "$$d/doc"; echo "Removed $$d/doc"; fi; \
	done
	@echo "Default configs remain in $(DOCTOR_HOME) (remove manually if you want them gone)"

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

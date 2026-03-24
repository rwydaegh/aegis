PYTHON ?= $(shell command -v py >/dev/null 2>&1 && echo "py -3.12" || echo "python")

.PHONY: test test-all lint format docs viewer

test:
	$(PYTHON) -m pytest tests/ -m "not slow" -x

test-all:
	$(PYTHON) -m pytest tests/

lint:
	$(PYTHON) -m ruff check src/ tests/

format:
	$(PYTHON) -m ruff format src/ tests/

docs:
	$(PYTHON) -m mkdocs serve

viewer:
	$(PYTHON) -m aegis.viewer --location "Ghent, Belgium"

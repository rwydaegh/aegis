.PHONY: test test-all lint format docs viewer

test:
	py -3.12 -m pytest tests/ -m "not slow" -x

test-all:
	py -3.12 -m pytest tests/

lint:
	py -3.12 -m ruff check src/ tests/

format:
	py -3.12 -m ruff format src/ tests/

docs:
	py -3.12 -m mkdocs serve

viewer:
	py -3.12 -m aegis.viewer --location "Ghent, Belgium"

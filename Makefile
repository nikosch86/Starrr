.PHONY: test lint coverage install run clean venv format typecheck all check

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

venv:
	python3 -m venv $(VENV)

test: venv
	$(PYTHON) -m pytest tests/ -v

lint: venv
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

format: venv
	$(PYTHON) -m ruff format .

typecheck: venv
	$(PYTHON) -m mypy app.py --ignore-missing-imports

coverage: venv
	$(PYTHON) -m pytest tests/ --cov=. --cov-report=html --cov-report=term --cov-fail-under=95

install: venv
	$(PIP) install -r requirements.txt

run: venv
	$(PYTHON) app.py

# Run all quality checks
check: lint typecheck test

# Run everything including coverage
all: check coverage

clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf $(VENV)
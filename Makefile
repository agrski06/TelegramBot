.PHONY: help test test-quick test-coverage test-unit test-integration clean install run

help:
	@echo "DoomStopper - Makefile commands"
	@echo ""
	@echo "  make install          - Install dependencies"
	@echo "  make test            - Run all tests with coverage"
	@echo "  make test-quick      - Run tests without coverage"
	@echo "  make test-coverage   - Run tests with HTML coverage report"
	@echo "  make test-unit       - Run only unit tests"
	@echo "  make test-integration - Run only integration tests"
	@echo "  make clean           - Clean up generated files"
	@echo "  make run             - Run the application"

install:
	pip install -r requirements.txt

test:
	pytest -v --cov=. --cov-report=term-missing

test-quick:
	pytest -v

test-coverage:
	pytest -v --cov=. --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-unit:
	pytest -v -m unit

test-integration:
	pytest -v -m integration

clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.db" -delete

run:
	python app.py
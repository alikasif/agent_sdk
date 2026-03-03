.PHONY: install test lint format docker-build docker-run clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=agent_sdk --cov-report=term-missing tests/

lint:
	ruff check agent_sdk/ tests/
	mypy agent_sdk/

format:
	ruff format agent_sdk/ tests/

docker-build:
	docker compose build

docker-run:
	docker compose up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache dist build *.egg-info

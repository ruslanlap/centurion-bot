.PHONY: help install dev lint format typecheck test run docker-build docker-up docker-down docker-logs clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .

dev: ## Install dev dependencies
	pip install -e ".[dev]"

lint: ## Run linter (ruff)
	ruff check centurion_bot/ tests/

format: ## Auto-format code
	ruff check --fix centurion_bot/ tests/
	ruff format centurion_bot/ tests/

typecheck: ## Run type checker (mypy)
	mypy centurion_bot/

test: ## Run tests
	pytest tests/ -v

run: ## Run the bot locally (polling mode)
	python -m centurion_bot

docker-build: ## Build Docker image
	docker compose build

docker-up: ## Start bot in Docker (detached)
	docker compose up -d

docker-down: ## Stop bot in Docker
	docker compose down

docker-logs: ## Show Docker logs
	docker compose logs -f bot

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .mypy_cache .pytest_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

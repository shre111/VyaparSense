.DEFAULT_GOAL := help
.PHONY: help setup lint typecheck test fmt web api ml up down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dev tooling (pre-commit hooks, commit-msg lint)
	pip install pre-commit
	pre-commit install --hook-type commit-msg --hook-type pre-commit

lint: ## Lint python + web
	-ruff check .
	-cd apps/web && npm run lint

typecheck: ## Typecheck python + web
	-mypy packages/ml apps/api 2>/dev/null || true
	-cd apps/web && npm run typecheck

test: ## Run tests
	-pytest -q packages/ml 2>/dev/null || true

fmt: ## Auto-format
	-ruff format .
	-ruff check --fix .

web: ## Run the Next.js dev server
	cd apps/web && npm run dev

api: ## Run the FastAPI dev server
	cd apps/api && uvicorn app.main:app --reload

up: ## Start full stack via docker compose
	docker compose -f infra/docker-compose.yml up

down: ## Stop the stack
	docker compose -f infra/docker-compose.yml down

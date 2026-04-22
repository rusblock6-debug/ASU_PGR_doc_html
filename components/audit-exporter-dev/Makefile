.PHONY: help
help: targets

.PHONY: targets
targets:
	@echo "\033[34mDevelopment Targets\033[0m"
	@echo "\033[34m---------------------------------------------------------------\033[0m"
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'


# Development targets
# -------------

.PHONY: sync
sync: ## Install dependencies
	uv sync

.PHONY: start
start: ## Starts the server
	uv run uvicorn src.main:app --reload


.PHONY: migrate
migrate:  ## Run the migrations
	uv run alembic upgrade head

.PHONY: rollback
rollback: ## Rollback migrations one level
	uv run alembic downgrade -1

.PHONY: reset-database
reset-database: ## Rollback all migrations
	uv run alembic downgrade base

.PHONY: generate-migration
generate-migration: ## Generate a new migration
	@read -p "Enter migration message: " message; \
	uv run alembic revision --autogenerate -m "$$message"




# Check, lint and format targets
# ------------------------------

.PHONY: lint
lint: ## Run linter
	uv run ruff check

.PHONY: format
format: ## Run code formatter
	uv run ruff format
	uv run ruff check --fix

.PHONY: check-types
check-types: ## Check types
	uv run mypy src/app --install-types

.PHONE: setup-precommit
setup-precommit: ## Install all hooks
	uv run pre-commit install

.PHONE: check-precommit
check-precommit: ## Check
	uv run pre-commit run --all-files

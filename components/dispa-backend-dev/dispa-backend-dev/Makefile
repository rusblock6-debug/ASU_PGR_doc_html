# Makefile для запуска нагрузочных тестов VehicleServerManager (RabbitMQ)
# Выполнять из корня app/: make <цель>

.DEFAULT_GOAL := help

PYTEST = .venv/bin/python -m pytest
LOAD_TEST = app/tests/services/rabbitmq/test_vehicle_server_manager_load.py

# Introspection targets
# ---------------------

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
	uv sync --all-groups

PORT ?= 8000
.PHONY: start
start: ## Starts the server (PORT=8061 для своего порта)
	uv run uvicorn app.main:app --reload --app-dir src --port $(PORT)

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





.PHONY: test-load-rabbitmq
test-load-rabbitmq-mem: ## In-memory (явно), те же параметры
	$(PYTEST) $(LOAD_TEST)::test_vehicle_server_manager_load -v -s $(if $(VEHS),--vehicles $(VEHS),) $(if $(DURATION),--load-duration $(DURATION),)


.PHONY: test-load-rabbitmq-real
test-load-rabbitmq-real: ## Реальный RabbitMQ; нужен запущенный брокер (URL из настроек)
	$(PYTEST) $(LOAD_TEST)::test_vehicle_server_manager_load -v -s --real-broker $(if $(VEHS),--vehicles $(VEHS),) $(if $(DURATION),--load-duration $(DURATION),)


.PHONY: test-uneven-queues
test-uneven-queues: ## Тест неравномерных очередей (реальный RabbitMQ). Опционально: VEHICLES=N
	$(PYTEST) $(LOAD_TEST)::test_uneven_queues_drain_summary -v -s --real-broker $(if $(VEHS),--vehicles $(VEHS),)

# Build configuration
# -------------------

# Загружаем переменные из .env, если файл существует
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Миграции — путь к папке + название таблицы (можно переопределить)
MIGRATIONS_DIR ?= clickhouse_migrations
MIGRATIONS_TABLE ?= schema_migrations
CLICKHOUSE_DSN = clickhouse://$(CLICKHOUSE_HOST):$(CLICKHOUSE_MIGRATION_PORT)?username=$(CLICKHOUSE_USERNAME)&password=$(CLICKHOUSE_PASSWORD)&database=$(CLICKHOUSE_DATABASE)&x-migrations-table-engine=MergeTree&x-multi-statement=true
# Для production лучше задавать через .env или переменные окружения
# Пример: export CLICKHOUSE_DSN="clickhouse://user:pass@ch-host:8123/analytics?x-migrations-table-engine=MergeTree"

# Introspection targets
# ---------------------

.PHONY: help
help: header targets

.PHONY: header
header:
	@echo "\033[34mEnvironment\033[0m"
	@echo "\033[34m---------------------------------------------------------------\033[0m"
	@printf "\033[33m%-23s\033[0m" "PROJECT_NAME"
	@printf "\033[35m%s\033[0m" $(PROJECT_NAME)
	@echo ""
	@printf "\033[33m%-23s\033[0m" "PROJECT_VERSION"
	@printf "\033[35m%s\033[0m" $(PROJECT_VERSION)
	@echo ""
	@printf "\033[33m%-23s\033[0m" "GIT_REVISION"
	@printf "\033[35m%s\033[0m" $(GIT_REVISION)
	@echo "\n"

.PHONY: targets
targets:
	@echo "\033[34mDevelopment Targets\033[0m"
	@echo "\033[34m---------------------------------------------------------------\033[0m"
	@perl -nle'print $$& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# Development targets
# -------------

.PHONY: sync
sync: ## Install dependencies
	uv sync

.PHONY: start
start: ## Starts the server
	uv run -m src

# Миграции — golang-migrate
# -------------------------

.PHONY: install-migrate
install-migrate: ## Install golang-migrate CLI (if not installed)
	@which migrate >/dev/null || (echo "Installing golang-migrate..." && go install -tags 'clickhouse' github.com/golang-migrate/migrate/v4/cmd/migrate@latest)

.PHONY: migrate-create
migrate-create: install-migrate ## Create a new migration pair: make migrate-create name=add_events_table
	@migrate create -ext sql -dir $(MIGRATIONS_DIR) -seq $(name)

.PHONY: migrate-up
migrate-up: install-migrate ## Apply all pending migrations
	@migrate -path $(MIGRATIONS_DIR) -database "$(CLICKHOUSE_DSN)" -verbose up

.PHONY: migrate-down
migrate-down: install-migrate ## Rollback the last migration
	@migrate -path $(MIGRATIONS_DIR) -database "$(CLICKHOUSE_DSN)" -verbose down

.PHONY: migrate-force
migrate-force: install-migrate ## Force set version (use when DB is dirty) — example: make migrate-force v=3
	@migrate -path $(MIGRATIONS_DIR) -database "$(CLICKHOUSE_DSN)" force $(v)

.PHONY: migrate-version
migrate-version: install-migrate ## Show current migration version
	@migrate -path $(MIGRATIONS_DIR) -database "$(CLICKHOUSE_DSN)" version

.PHONY: migrate-drop
migrate-drop: install-migrate ## Drop everything (dangerous!)
	@migrate -path $(MIGRATIONS_DIR) -database "$(CLICKHOUSE_DSN)" drop -f

# Псевдонимы, как в твоём старом Makefile
.PHONY: migrate
migrate: migrate-up ## Run the migrations (alias)

.PHONY: rollback
rollback: migrate-down ## Rollback migrations one level (alias)

.PHONY: reset-database
reset-database: migrate-drop ## Dangerous: drop all tables and reset migrations (alias)

.PHONY: generate-migration
generate-migration: migrate-create ## Generate a new migration (alias)

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
	uv run mypy src --explicit-package-bases --install-types

.PHONY: setup-precommit
setup-precommit: ## Install all hooks
	uv run pre-commit install

.PHONY: check-precommit
check-precommit: ## Check
	uv run pre-commit run --all-files

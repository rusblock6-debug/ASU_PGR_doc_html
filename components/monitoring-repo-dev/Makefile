.PHONY: help down stop restart logs ps clean init init-bort init-server dev-bort dev-bort-bootstrap bootstrap-bort-env bootstrap-bort-manual-env dev-server check-migrations build-bort build-server uv-index-url uv-index-remove help-uv update-settings-bort-service pull-and-restart-settings-bort-service

GREEN  :=
YELLOW :=
NC     :=

DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null || echo "docker compose")

COMPOSE_BORT := docker-compose.bort.yaml
COMPOSE_SETTINGS := docker-compose.settings-bort.yaml
COMPOSE_SERVER := docker-compose.server.yaml
COMPOSE_MONITORING := docker-compose.monitoring.yaml

ENV_FILE ?= .env_server_dev
BRANCH ?= dev

help:
	@echo "${GREEN}Доступные команды:${NC}"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${YELLOW}%-20s${NC} %s\n", $$1, $$2}'

init:
	@echo "${GREEN}Инициализация всех проектов...${NC}"
	@bash scripts/clone_cursor_rules.sh
	@bash scripts/clone_bort.sh
	@echo "${GREEN}Все проекты инициализированы${NC}"

.env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "${GREEN}Создан файл .env из .env.example${NC}"; \
		echo "${YELLOW}Пожалуйста, отредактируйте .env с вашими настройками${NC}"; \
	else \
		echo "${YELLOW}Файл .env уже существует${NC}"; \
	fi

init-bort: .env ## Инициализация бортовой части (клонирование репозиториев из раздела Dispa bort)
	@echo "${GREEN}Инициализация бортовой части...${NC}"
	@bash scripts/clone_cursor_rules.sh
	@bash scripts/clone_bort.sh
	@echo "${GREEN}Бортовая часть инициализирована${NC}"

init-server: .env ## Инициализация серверной части (клонирование репозиториев из раздела Dispa Server)
	@echo "${GREEN}Инициализация серверной части...${NC}"
	@bash scripts/clone_server.sh
	@echo "${GREEN}Серверная часть инициализирована${NC}"

build-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) build

build-bort-clean:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) build --no-cache

build-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) build

build-server-clean:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) build --no-cache

dev-bort: init-bort ## Запустить бортовую часть в режиме разработки (автоматическая пересборка образов)
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
		if [ ! -f "$$ENV_FILE" ]; then \
			echo "${YELLOW}Ошибка: Файл $$ENV_FILE не найден!${NC}"; \
			exit 1; \
		fi; \
		echo "${GREEN}Используется env файл: $$ENV_FILE${NC}"; \
		DEFAULT_ENV="$$ENV_FILE"; \
	else \
		if [ ! -f ".env" ]; then \
			echo "${YELLOW}Ошибка: Файл .env не найден!${NC}"; \
			echo "${YELLOW}Создайте .env файл или используйте: make dev-bort e=bort_1${NC}"; \
			exit 1; \
		fi; \
		echo "${GREEN}Используется дефолтный .env файл${NC}"; \
		DEFAULT_ENV=".env"; \
	fi && \
	echo "Загружаем переменные из $$DEFAULT_ENV..." && \
	set -a && . ./$$DEFAULT_ENV && set +a && \
	echo "Пересборка образов бортовой части..." && \
	$(DOCKER_COMPOSE) --env-file "$$DEFAULT_ENV" -f $(COMPOSE_BORT) build --no-cache && \
	# echo "Очистка build cache..." && \
	# docker builder prune -f && \
	echo "Запуск бортовой части в режиме разработки..." && \
	ENVIRONMENT=development $(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$DEFAULT_ENV" up -d --force-recreate --remove-orphans --pull always && \
	echo "${GREEN}Бортовая часть запущена${NC}"
	@echo ""
	@echo "${GREEN}=== URLs бортовых сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}Redis (кэш):${NC}           localhost:6379"
	@echo "${YELLOW}PostgreSQL (БД):${NC}       localhost:5432"
	@echo "${YELLOW}NanoMQ MQTT:${NC}           localhost:1883"
	@echo "${YELLOW}NanoMQ WebSocket:${NC}      ws://localhost:8083/mqtt"
	@echo "${YELLOW}NanoMQ Admin:${NC}          http://localhost:8081"
	@echo "${YELLOW}eKuiper:${NC}               http://localhost:9081"
	@echo "${YELLOW}eKuiper Manager:${NC}       http://localhost:9083"
	@echo "${YELLOW}Manager credentials:${NC}   admin:public"
	@echo "${YELLOW}Trip Service Backend:${NC}  http://localhost:8000"
	@echo "${YELLOW}Graph Service Backend:${NC} http://localhost:5001"
	@echo "${YELLOW}Main Frontend:${NC}         http://localhost:3000"
	@echo "${YELLOW}Graph Service Frontend:${NC} http://localhost:3001"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9999"
	@echo ""
	@echo "${GREEN}=== Мониторинг ===${NC}"
	@echo ""
	@echo "${YELLOW}Prometheus:${NC}            http://localhost:9090"
	@echo "${YELLOW}Grafana:${NC}               http://localhost:3002"
	@echo "${YELLOW}Grafana credentials:${NC}   admin:admin"
	@echo "${YELLOW}Node Exporter:${NC}         http://localhost:9100/metrics"
	@echo "${YELLOW}Postgres Exporter:${NC}     http://localhost:9187/metrics"
	@echo "${YELLOW}Redis Exporter:${NC}        http://localhost:9121/metrics"
	@echo ""

bootstrap-bort-env: ## Поднять settings-bort и сгенерировать env через bootstrap_with_settings.sh (без запуска bort compose)
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_TAG="$(e)"; \
		BASE_ENV=""; \
	else \
		ENV_TAG="settings_generated"; \
		BASE_ENV=".env"; \
	fi && \
	OUTPUT_ENV=".env_$$ENV_TAG" && \
	if [ -n "$$BASE_ENV" ] && [ -f "$$BASE_ENV" ]; then \
		echo "${GREEN}Используется base env файл: $$BASE_ENV${NC}"; \
		BASE_ARG="--base-env-file $$BASE_ENV"; \
	else \
		echo "${YELLOW}Base env не используется (или файл не найден), продолжаем без него${NC}"; \
		BASE_ARG=""; \
	fi && \
	if [ -z "$$BASE_ARG" ] && [ -f "$$OUTPUT_ENV" ]; then \
		echo "${YELLOW}Удаляем старый $$OUTPUT_ENV перед генерацией${NC}"; \
		rm -f "$$OUTPUT_ENV"; \
	fi && \
	echo "${GREEN}Итоговый env файл: $$OUTPUT_ENV${NC}" && \
	bash scripts/bootstrap_with_settings.sh \
		--settings-compose-file $(COMPOSE_SETTINGS) \
		$$BASE_ARG \
		--settings-service settings-service \
		--output-env-file "$$OUTPUT_ENV" && \
	echo "${GREEN}Env готов:${NC} $$OUTPUT_ENV" && \
	echo "Запуск bort отдельно: make dev-bort e=$$ENV_TAG"

bootstrap-bort-manual-env: ## Поднять settings-bort и ждать ручной init, затем сгенерировать env (без запуска bort compose)
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_TAG="$(e)"; \
		BASE_ENV=""; \
	else \
		ENV_TAG="settings_generated"; \
		BASE_ENV=".env"; \
	fi && \
	OUTPUT_ENV=".env_$$ENV_TAG" && \
	if [ -n "$$BASE_ENV" ] && [ -f "$$BASE_ENV" ]; then \
		echo "${GREEN}Используется base env файл: $$BASE_ENV${NC}"; \
		BASE_ARG="--base-env-file $$BASE_ENV"; \
	else \
		echo "${YELLOW}Base env не используется (или файл не найден), продолжаем без него${NC}"; \
		BASE_ARG=""; \
	fi && \
	if [ -z "$$BASE_ARG" ] && [ -f "$$OUTPUT_ENV" ]; then \
		echo "${YELLOW}Удаляем старый $$OUTPUT_ENV перед генерацией${NC}"; \
		rm -f "$$OUTPUT_ENV"; \
	fi && \
	echo "${GREEN}Итоговый env файл: $$OUTPUT_ENV${NC}" && \
	echo "Ожидание ручной инициализации через settings-bort UI/curl..." && \
	bash scripts/bootstrap_with_settings.sh \
		--settings-compose-file $(COMPOSE_SETTINGS) \
		$$BASE_ARG \
		--settings-service settings-service \
		--output-env-file "$$OUTPUT_ENV" \
		--skip-init && \
	echo "${GREEN}Env готов:${NC} $$OUTPUT_ENV" && \
	echo "Запуск bort отдельно: make dev-bort e=$$ENV_TAG"

dev-bort-bootstrap: ## Полный flow: bootstrap env (auto/manual) + запуск dev-bort (manual=1 для ручного init)
	@set -e && cd $(shell pwd) && \
	if [ "$(manual)" = "1" ]; then \
		BOOTSTRAP_TARGET="bootstrap-bort-manual-env"; \
	else \
		BOOTSTRAP_TARGET="bootstrap-bort-env"; \
	fi && \
	if [ -n "$(e)" ]; then \
		ENV_TAG="$(e)"; \
		$(MAKE) $$BOOTSTRAP_TARGET e="$$ENV_TAG"; \
	else \
		ENV_TAG="settings_generated"; \
		$(MAKE) $$BOOTSTRAP_TARGET; \
	fi && \
	$(MAKE) dev-bort e="$$ENV_TAG"

dev-server: init-server ## Запустить серверную часть в режиме разработки (автоматическая пересборка образов). Используйте ENV_FILE=.env для .env
	@set -e && \
	echo "${GREEN}Используется env файл: $(ENV_FILE)${NC}" && \
	echo "Загружаем переменные из $(ENV_FILE)..." && \
	echo "Пересборка образов серверной части..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) build --no-cache && \
	# echo "Очистка build cache..." && \
	# docker builder prune -f && \
	echo "Запуск серверной части в режиме разработки..." && \
	ENVIRONMENT=development $(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) up -d --force-recreate --remove-orphans --pull always && \
	echo "${GREEN}Серверная часть запущена${NC}" && \
	echo "Ожидание завершения настройки MinIO..." && \
	sleep 5 && \
	if docker ps -a --filter "name=minio-setup" --filter "status=exited" --format "{{.Names}}" | grep -q "minio-setup"; then \
		echo "Удаление init-контейнера minio-setup..." && \
		docker rm minio-setup >/dev/null 2>&1 || true; \
	fi
	@echo ""
	@echo "${GREEN}=== URLs серверных сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}PostgreSQL (БД):${NC}       localhost:5433"
	@echo "${YELLOW}Redis (кэш):${NC}           localhost:6379"
	@ENTERPRISE_PORT=$$(grep -E '^ENTERPRISE_SERVICE_PORT=' "$(ENV_FILE)" 2>/dev/null | tail -n 1 | cut -d= -f2); \
	ENTERPRISE_PORT=$${ENTERPRISE_PORT:-8002}; \
	echo "${YELLOW}Enterprise Service:${NC}    http://localhost:$${ENTERPRISE_PORT}"
	@echo "${YELLOW}Client (Frontend):${NC}      http://localhost:5173 & 80"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9998"
	@echo ""

monitoring: ## Запустить мониторинг отдельно от основных сервисов
	@set -e && \
	echo "Запуск сервисов мониторинга..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) up -d && \
	bash ./config/vector/start.sh && \
	echo "${GREEN}Мониторинг запущен${NC}"
	@echo ""
	@echo "${GREEN}=== URLs мониторинга ===${NC}"
	@echo ""
	@echo "${YELLOW}Prometheus:${NC}            http://localhost:9090"
	@echo "${YELLOW}Grafana:${NC}               http://localhost:3002"
	@echo "${YELLOW}Grafana credentials:${NC}   admin:admin"
	@echo "${YELLOW}Node Exporter:${NC}         http://localhost:9100/metrics"
	@echo "${YELLOW}Postgres Exporter:${NC}     http://localhost:9187/metrics"
	@echo "${YELLOW}Redis Exporter:${NC}        http://localhost:9121/metrics"
	@echo "${YELLOW}cAdvisor:${NC}              http://localhost:8080"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9999"
	@echo ""

down:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) down
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) down
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) down
	@echo "${GREEN}Все сервисы остановлены${NC}"

stop:
	@make down

down-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) down
	@echo "${GREEN}Бортовая часть остановлена${NC}"

down-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) down
	@echo "${GREEN}Серверная часть остановлена${NC}"

down-monitoring:
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) down
	@echo "${GREEN}Мониторинг остановлен${NC}"

restart:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) restart
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) restart
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) restart
	@echo "${GREEN}Сервисы перезапущены${NC}"

restart-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) restart
	@echo "${GREEN}Бортовая часть перезапущена${NC}"

restart-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) restart
	@echo "${GREEN}Серверная часть перезапущена${NC}"

restart-monitoring:
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) restart
	@echo "${GREEN}Мониторинг перезапущен${NC}"

logs:
	@echo "${YELLOW}Используйте logs-bort, logs-server или logs-monitoring${NC}"

logs-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) logs -f

logs-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) logs -f

logs-monitoring:
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) logs -f

ps:
	@echo "${GREEN}=== Бортовая часть ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) ps
	@echo ""
	@echo "${GREEN}=== Серверная часть ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) ps
	@echo ""
	@echo "${GREEN}=== Мониторинг ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) ps

ps-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) ps

ps-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) ps

ps-monitoring:
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) ps

urls-monitoring:
	@echo ""
	@echo "${GREEN}=== URLs мониторинга ===${NC}"
	@echo ""
	@echo "${YELLOW}Prometheus:${NC}            http://localhost:9090"
	@echo "${YELLOW}Grafana:${NC}               http://localhost:3002"
	@echo "${YELLOW}Grafana credentials:${NC}   admin:admin"
	@echo "${YELLOW}Node Exporter:${NC}         http://localhost:9100/metrics"
	@echo "${YELLOW}Postgres Exporter:${NC}     http://localhost:9187/metrics"
	@echo "${YELLOW}Redis Exporter:${NC}        http://localhost:9121/metrics"
	@echo "${YELLOW}cAdvisor:${NC}              http://localhost:8080"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9999"
	@echo ""

urls:
	@echo ""
	@echo "${GREEN}=== URLs бортовых сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}Redis (кэш):${NC}           localhost:6379"
	@echo "${YELLOW}PostgreSQL (БД):${NC}       localhost:5432"
	@echo "${YELLOW}NanoMQ MQTT:${NC}           localhost:1883"
	@echo "${YELLOW}NanoMQ WebSocket:${NC}      ws://localhost:8083/mqtt"
	@echo "${YELLOW}NanoMQ Admin:${NC}          http://localhost:8081"
	@echo "${YELLOW}eKuiper:${NC}               http://localhost:9081"
	@echo "${YELLOW}eKuiper Manager:${NC}       http://localhost:9083"
	@echo "${YELLOW}Manager credentials:${NC}   admin:public"
	@echo "${YELLOW}Trip Service Backend:${NC}  http://localhost:8000"
	@echo "${YELLOW}Graph Service Backend:${NC} http://localhost:5001"
	@echo "${YELLOW}Main Frontend:${NC}         http://localhost:3000"
	@echo "${YELLOW}Graph Service Frontend:${NC} http://localhost:3001"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9999"
	@echo ""
	@echo "${GREEN}=== Мониторинг ===${NC}"
	@echo ""
	@echo "${YELLOW}Prometheus:${NC}            http://localhost:9090"
	@echo "${YELLOW}Grafana:${NC}               http://localhost:3002"
	@echo "${YELLOW}Grafana credentials:${NC}   admin:admin"
	@echo "${YELLOW}Node Exporter:${NC}         http://localhost:9100/metrics"
	@echo "${YELLOW}Postgres Exporter:${NC}     http://localhost:9187/metrics"
	@echo "${YELLOW}Redis Exporter:${NC}        http://localhost:9121/metrics"
	@echo ""
	@echo "${GREEN}=== URLs серверных сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}ClickHouse HTTP:${NC}       http://localhost:8123"
	@echo "${YELLOW}ClickHouse Native:${NC}     localhost:9000"
	@echo "${YELLOW}Trino (SQL):${NC}           http://localhost:8080"
	@echo "${YELLOW}Airbyte (интеграция):${NC}  http://localhost:8000"
	@echo "${YELLOW}Superset (BI):${NC}         http://localhost:8088"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9998"
	@echo ""

urls-bort:
	@echo ""
	@echo "${GREEN}=== URLs бортовых сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}Redis (кэш):${NC}           localhost:6379"
	@echo "${YELLOW}PostgreSQL (БД):${NC}       localhost:5432"
	@echo "${YELLOW}NanoMQ MQTT:${NC}           localhost:1883"
	@echo "${YELLOW}NanoMQ WebSocket:${NC}      ws://localhost:8083/mqtt"
	@echo "${YELLOW}NanoMQ Admin:${NC}          http://localhost:8081"
	@echo "${YELLOW}eKuiper:${NC}               http://localhost:9081"
	@echo "${YELLOW}eKuiper Manager:${NC}       http://localhost:9083"
	@echo "${YELLOW}Manager credentials:${NC}   admin:public"
	@echo "${YELLOW}Trip Service Backend:${NC}  http://localhost:8000"
	@echo "${YELLOW}Graph Service Backend:${NC} http://localhost:5001"
	@echo "${YELLOW}Main Frontend:${NC}         http://localhost:3000"
	@echo "${YELLOW}Graph Service Frontend:${NC} http://localhost:3001"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9999"
	@echo ""
	@echo "${GREEN}=== Мониторинг ===${NC}"
	@echo ""
	@echo "${YELLOW}Prometheus:${NC}            http://localhost:9090"
	@echo "${YELLOW}Grafana:${NC}               http://localhost:3002"
	@echo "${YELLOW}Grafana credentials:${NC}   admin:admin"
	@echo "${YELLOW}Node Exporter:${NC}         http://localhost:9100/metrics"
	@echo "${YELLOW}Postgres Exporter:${NC}     http://localhost:9187/metrics"
	@echo "${YELLOW}Redis Exporter:${NC}        http://localhost:9121/metrics"
	@echo ""

urls-server: ## Показать URLs серверных сервисов
	@echo ""
	@echo "${GREEN}=== URLs серверных сервисов ===${NC}"
	@echo ""
	@echo "${YELLOW}PostgreSQL (БД):${NC}       localhost:5433"
	@echo "${YELLOW}Redis (кэш):${NC}           localhost:6379"
	@ENTERPRISE_PORT=$$(grep -E '^ENTERPRISE_SERVICE_PORT=' "$(ENV_FILE)" 2>/dev/null | tail -n 1 | cut -d= -f2); \
	ENTERPRISE_PORT=$${ENTERPRISE_PORT:-8002}; \
	echo "${YELLOW}Enterprise Service:${NC}    http://localhost:$${ENTERPRISE_PORT}"
	@echo "${YELLOW}Client (Frontend):${NC}      http://localhost:5173 & 80"
	@echo "${YELLOW}Dozzle (логи):${NC}         http://localhost:9998"
	@echo ""

health:
	@echo "${GREEN}=== Бортовая часть ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) ps --format json | jq -r '.[] | "\(.Name): \(.Health)"'
	@echo ""
	@echo "${GREEN}=== Серверная часть ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) ps --format json | jq -r '.[] | "\(.Name): \(.Health)"'
	@echo ""
	@echo "${GREEN}=== Мониторинг ===${NC}"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) ps --format json | jq -r '.[] | "\(.Name): \(.Health)"'

# clean-logs:
# 	@echo "${GREEN}Очистка логов...${NC}"
# 	@rm -rf logs/*
# 	@mkdir -p logs/{clickhouse,superset}
# 	@echo "${GREEN}Логи очищены${NC}"

backup-volumes:
	@echo "${GREEN}Создание резервной копии volumes...${NC}"
	@mkdir -p backups
	@docker run --rm \
		-v dispatching-postgres-data:/data \
		-v $(PWD)/backups:/backup \
		alpine tar czf /backup/postgres-data-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "${GREEN}Резервная копия создана${NC}"

redis-cli:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) exec redis redis-cli

psql:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) exec postgres psql -U postgres -d dispatching

clickhouse-client:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) exec clickhouse clickhouse-client

pull:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) pull
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) pull
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) pull

pull-bort:
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) pull

pull-server:
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) pull

pull-monitoring:
	$(DOCKER_COMPOSE) -f $(COMPOSE_MONITORING) pull

stats:
	docker stats --no-stream

prune: ## Удалить неиспользуемые Docker ресурсы
	docker system prune -f
	@echo "${GREEN}Неиспользуемые ресурсы удалены${NC}"

prune-builder: ## Очистить только build cache
	docker builder prune -f
	@echo "${GREEN}Build cache очищен${NC}"

test-ekuiper: ## Запуск БЫСТРЫХ тестов (БЕЗ E2E, ~30 сек)
	@echo "${GREEN}Запуск быстрых тестов eKuiper (без E2E)...${NC}"
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) run --rm pytest
	@echo "${GREEN}Тесты завершены${NC}"

test-ekuiper-full: ## Запуск ВСЕХ тестов включая E2E (~2.5 мин)
	@echo "${GREEN}Запуск ВСЕХ тестов eKuiper (с E2E)...${NC}"
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) run --rm pytest pytest --run-e2e -v
	@echo "${GREEN}Все тесты завершены${NC}"

test-ekuiper-with-mocks: ## Запуск тестов с моками БЕЗ E2E (~30 сек)
	@echo "${GREEN}Запуск тестов с моками (без E2E)...${NC}"
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) run --rm pytest pytest --with-mocks -v
	@echo "${GREEN}Тесты завершены${NC}"

test-ekuiper-with-mocks-full: ## Запуск тестов с моками + E2E (~2.5 мин)
	@echo "${GREEN}Запуск тестов с моками (включая E2E)...${NC}"
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) run --rm pytest pytest --with-mocks --run-e2e -v
	@echo "${GREEN}Тесты завершены${NC}"

test-ekuiper-verbose: ## Запуск тестов с подробным выводом
	@echo "${GREEN}Запуск тестов eKuiper (verbose, без E2E)...${NC}"
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) run --rm pytest pytest -vv
	@echo "${GREEN}Тесты завершены${NC}"

check-migrations: ## Проверить целостность миграций во всех сервисах
	@echo "${GREEN}Проверка целостности миграций...${NC}"
	@python3 scripts/check_migrations.py
	@echo "${GREEN}Проверка завершена${NC}"

update-bort-service:
ifndef SERVICE
	$(error SERVICE не задан. Использование: make update-bort-service SERVICE=graph-service-backend e=bort_1)
endif
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	if [ ! -f "$$ENV_FILE" ]; then \
		echo "${YELLOW}Ошибка: Файл $$ENV_FILE не найден!${NC}"; \
		exit 1; \
	fi && \
	echo "${GREEN}Используется env файл: $$ENV_FILE${NC}" && \
	set -a && . ./$$ENV_FILE && set +a && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_BORT) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Пересборка сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" build --no-cache $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён${NC}"

update-settings-bort-service:
ifndef SERVICE
	$(error SERVICE не задан. Использование: make update-settings-bort-service SERVICE=settings-service e=bort_1)
endif
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	if [ -f "$$ENV_FILE" ]; then \
		echo "${GREEN}Используется env файл: $$ENV_FILE${NC}"; \
		ENV_ARGS="--env-file $$ENV_FILE"; \
	else \
		echo "${YELLOW}Файл $$ENV_FILE не найден, продолжаем с дефолтами $(COMPOSE_SETTINGS)${NC}"; \
		ENV_ARGS=""; \
	fi && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_SETTINGS) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Пересборка сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS build --no-cache $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён${NC}"

update-server-service:
ifndef SERVICE
	$(error SERVICE не задан. Использование: make update-server-service SERVICE=enterprise-service)
endif
	@set -e && \
	echo "${GREEN}Используется env файл: $(ENV_FILE)${NC}" && \
	echo "Загружаем переменные из $(ENV_FILE)..." && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_SERVER) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Пересборка сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) build --no-cache $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён${NC}"

pull-and-restart-bort-service: ## Pull и перезапуск одного сервиса bort (из registry)
ifndef SERVICE
	$(error SERVICE не задан. Использование: make pull-and-restart-bort-service SERVICE=graph-service-backend e=bort_1)
endif
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	if [ ! -f "$$ENV_FILE" ]; then \
		echo "${YELLOW}Ошибка: Файл $$ENV_FILE не найден!${NC}"; \
		exit 1; \
	fi && \
	echo "${GREEN}Используется env файл: $$ENV_FILE${NC}" && \
	set -a && . ./$$ENV_FILE && set +a && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_BORT) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Docker login в registry..." && \
	docker login registry.dmi-msk.ru -u "$$CI_REGISTRY_USER" -p "$$CI_REGISTRY_PASSWORD" && \
	echo "Pulling образа для $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" pull $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён (pull)${NC}"

pull-and-restart-settings-bort-service: ## Pull и перезапуск одного сервиса settings-bort (из registry)
ifndef SERVICE
	$(error SERVICE не задан. Использование: make pull-and-restart-settings-bort-service SERVICE=settings-service e=bort_1)
endif
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	if [ -f "$$ENV_FILE" ]; then \
		echo "${GREEN}Используется env файл: $$ENV_FILE${NC}"; \
		ENV_ARGS="--env-file $$ENV_FILE"; \
	else \
		echo "${YELLOW}Файл $$ENV_FILE не найден, продолжаем с дефолтами $(COMPOSE_SETTINGS)${NC}"; \
		ENV_ARGS=""; \
	fi && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_SETTINGS) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Docker login в registry..." && \
	docker login registry.dmi-msk.ru -u "$$CI_REGISTRY_USER" -p "$$CI_REGISTRY_PASSWORD" && \
	echo "Pulling образа для $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS pull $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SETTINGS) $$ENV_ARGS up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён (pull)${NC}"

pull-and-restart-server-service: ## Pull и перезапуск одного сервиса server (из registry)
ifndef SERVICE
	$(error SERVICE не задан. Использование: make pull-and-restart-server-service SERVICE=enterprise-service)
endif
	@set -e && \
	echo "${GREEN}Используется env файл: $(ENV_FILE)${NC}" && \
	echo "Загружаем переменные из $(ENV_FILE)..." && \
	if ! $(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) config --services 2>/dev/null | grep -q "^$(SERVICE)$$"; then \
		echo "${YELLOW}Сервис $(SERVICE) не найден в $(COMPOSE_SERVER) - пропускаем${NC}"; \
		exit 0; \
	fi && \
	echo "Docker login в registry..." && \
	docker login registry.dmi-msk.ru -u "$$CI_REGISTRY_USER" -p "$$CI_REGISTRY_PASSWORD" && \
	echo "Pulling образа для $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) pull $(SERVICE) && \
	echo "Перезапуск сервиса $(SERVICE)..." && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) up -d --no-deps --force-recreate $(SERVICE) && \
	echo "${GREEN}Сервис $(SERVICE) обновлён (pull)${NC}"

pull-all-bort: ## Pull всех образов для bort
	@set -e && cd $(shell pwd) && \
	if [ -n "$(e)" ]; then \
		ENV_FILE=".env_$(e)"; \
	else \
		ENV_FILE=".env"; \
	fi && \
	echo "${GREEN}Pulling всех образов (bort)...${NC}" && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_BORT) --env-file "$$ENV_FILE" pull && \
	echo "${GREEN}Все образы загружены${NC}"

pull-all-server: ## Pull всех образов для server
	@set -e && \
	echo "${GREEN}Pulling всех образов (server)...${NC}" && \
	$(DOCKER_COMPOSE) -f $(COMPOSE_SERVER) --env-file $(ENV_FILE) pull && \
	echo "${GREEN}Все образы загружены${NC}"

uv-index-url:
	@echo "Установка глобального extra-index-url для uv (ветка: $(BRANCH))"
	mkdir -p ~/.config/uv/
	echo 'extra-index-url = ["https://'$${CI_REGISTRY_USER}':'$${CI_REGISTRY_PASSWORD}'@'$${CI_PIPY_DOMAIN}'/repository/pypi-$(BRANCH)-group/simple"]' > ~/.config/uv/uv.toml

uv-index-remove:
	@echo "Удаление файла конфигурации uv"
	rm -f ~/.config/uv/uv.toml

help-uv:
	@echo "Цели для управления конфигурацией uv (Nexus):"
	@echo "  uv-index-url [BRANCH=dev]   Создать конфигурацию uv для Nexus-репозитория pypi-<BRANCH>-group."
	@echo "                               Поддерживаемые ветки: dev, main, staging."
	@echo "                               Пример: make uv-index-url BRANCH=dev"
	@echo "  uv-index-remove              Удалить файл конфигурации uv (~/.config/uv/uv.toml)."
	@echo "                               Пример: make uv-index-remove"
	@echo ""

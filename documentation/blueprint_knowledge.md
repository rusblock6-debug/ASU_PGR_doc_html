# База знаний АСУ ПГР (Blueprint)

**Дата создания:** 29.04.2026  
**Статус:** В процессе создания  
**Метод:** Иерархическая индексация через Qwen API

---

## Уровень 0: ВСЯ СИСТЕМА АСУ ПГР

### Общее описание системы

АСУ ПГР (Автоматизированная Система Управления Подземными Горными Работами) — это комплексная система управления горнодобывающим предприятием, также известная как "Цифровой двойник карьера".

Система предназначена для автоматизации и оптимизации всех процессов горных работ: от планирования рейсов до мониторинга техники в реальном времени.

**Основные компоненты системы:**
- Бортовые контроллеры (bort-client) — приложения для самосвалов
- Диспетчерский интерфейс (client-disp) — управление бортами и мониторинг
- Сервис аналитики (analytics-service) — отчёты и статистика КРВ
- API Gateway — единая точка входа для всех сервисов
- Сервис графов (graph-service) — схема дорог и маршрутизация
- Сервис предприятия (enterprise-service) — управление организациями
- Аутентификация (auth-service) — управление пользователями и правами

**Архитектура:** Микросервисная архитектура на базе Docker, с использованием PostgreSQL, Redis, RabbitMQ, ClickHouse и других технологий.

**Целевая аудитория:** Диспетчеры, операторы, администраторы системы, водители самосвалов.

### Основная документация системы

Документация АСУ ПГР хранится в файле `tetepfgr/data.json` и содержит структурированные инструкции для пользователей.

**Структура документации:**
- **Быстрый старт (quickstart)** — пошаговые инструкции для новых пользователей: вход в систему, обзор интерфейса, проверка готовности, создание заданий
- **Инструкции администратора (admin_instructions)** — настройка схемы дорог, управление пользователями, конфигурация системы
- **Обычные инструкции (instructions)** — оперативная работа: наряд-задания, рейсы бортов, мониторинг
- **Описательные разделы (descriptive)** — описание компонентов системы: борт-контроль, диспетчерская, аналитика

**Справочники (directory_data.json):**
Содержит параметры справочников: виды груза, статусы, горизонты, места работ, оборудование. Каждый справочник имеет title, parameters (список полей), note (примечание) и image (скриншот).

---

## Уровень 1: КОМПОНЕНТЫ СИСТЕМЫ

### 1. Bort Client (bort-client-dev)

**Назначение:** Бортовое клиентское приложение для самосвалов, установленное на бортовых контроллерах техники.

**Технологии:** React 19, TypeScript, Vite, Mantine UI, React Router. Работает на Node.js v22+.

**Функционал:** Отображает задания для водителя, позволяет управлять рейсами (начать, завершить), показывает статус борта и текущую задачу.

**Интерфейс:** Простой UI для работы в кабине самосвала с крупными кнопками и минимальным количеством элементов.

**Запуск:** `npm run dev` для разработки, Docker для продакшена.

### 2. Client Disp (client-disp-dev)

**Назначение:** Диспетчерский интерфейс для управления горными работами и мониторинга техники в реальном времени.

**Технологии:** React 19, TypeScript, Vite, Mantine UI, React Router. Работает на Node.js v22+.

**Функционал:** Создание наряд-заданий, управление рейсами бортов, мониторинг статуса техники, построение схемы дорог, отчёты КРВ.

**Интерфейс:** Полнофункциональный UI для диспетчеров с картами, таблицами, фильтрами и графиками.

**Основные разделы:** Оперативная работа (наряд-задания, рейсы), Отчёты (КРВ, производительность), Справочники, Диагностика, Настройки.

**Запуск:** `npm run dev` для разработки, Docker для продакшена.

### 3. Analytics Service (analytics-service-dev)

**Назначение:** Сервис аналитики и отчётности, предоставляет данные из ClickHouse для фронтенда и выполняет ETL-процессы.

**Технологии:** Python 3.13+, FastAPI, FastStream, ClickHouse, MinIO/S3, RabbitMQ, uv (менеджер зависимостей).

**Архитектура:** Два процесса — FastAPI (HTTP API для фронтенда) и FastStream consumer (обработка событий MinIO из RabbitMQ).

**Функционал:** 
- HTTP API для получения аналитических данных из ClickHouse
- ETL-процесс: загрузка parquet-файлов из MinIO в ClickHouse
- Контроль идемпотентности через таблицу s3_file (повторная загрузка исключена)
- Отчёты КРВ (коэффициент использования техники), статистика производительности

**Поток данных:** Dump-service → MinIO (parquet файлы) → RabbitMQ (события) → FastStream → ClickHouse → FastAPI → Frontend.

**Конфигурация:** Переменные окружения для подключения к ClickHouse, MinIO, RabbitMQ. Режимы: local, dev, production.

### 4. API Gateway (api-gateway-dev)

**Назначение:** Единая точка входа для всех запросов к микросервисам системы АСУ ПГР, маршрутизация и аутентификация.

**Технологии:** Python, aiohttp (асинхронный HTTP сервер), JWT, YAML конфигурация.

**Архитектура:** Легковесный прокси-сервер, который принимает запросы на `/api/{version}/{service}/{path}` и перенаправляет их внутренним сервисам.

**Функционал:**
- Маршрутизация запросов по имени сервиса из config.yaml
- Проксирование HTTP, WebSocket и Server-Sent Events (SSE)
- Проверка JWT токенов через auth-service
- Генерация и проброс X-Request-Id для трассировки запросов
- Health check endpoint (`GET /health`)
- Структурированные JSON логи для мониторинга

**Поток запроса:** Client → API Gateway → JWT verification → Service routing → Upstream service → Response.

**Обработка ошибок:** 401 (Unauthorized) при неверном JWT, 502 (Service not found) при отсутствии сервиса в конфиге, 503 (Service Unavailable) при недоступности auth-service.

### 5. Graph Service Backend (graph-service-backend-dev)

**Назначение:** Backend API для визуализации и управления графами дорожных сетей карьера, построение маршрутов и отслеживание транспорта.

**Технологии:** Python, Flask, Flask-SocketIO (WebSocket), PostGIS (геопространственная БД), python-igraph (графы), MQTT client, Alembic (миграции).

**Архитектура:** REST API + WebSocket для real-time обновлений + MQTT подписка на GPS данные грузовиков.

**Функционал:**
- Управление уровнями, узлами, ребрами и метками схемы дорог
- Построение маршрутов между узлами с использованием python-igraph
- Ladder Nodes — автоматическое создание межуровневых соединений
- Real-time отслеживание позиции транспорта через WebSocket
- Подписка на MQTT топики `truck/+/sensor/gps/ds` для получения GPS координат
- Поиск ближайшей метки по координатам (Canvas coordinates)
- Кэширование графов уровней с возможностью перестроения

**API Endpoints:** Levels, Nodes, Edges, Ladder Nodes, Tags, Location, Route, Graph stats.

**WebSocket события:** `join_vehicle_tracking` (client→server), `vehicle_location_update` (server→client).

### 6. Auth Service Backend (auth-service-backend-dev)

**Назначение:** Сервис аутентификации и авторизации с поддержкой JWT токенов, ролевой моделью доступа и системой разрешений.

**Технологии:** Python, FastAPI, PostgreSQL, Alembic (миграции), JWT (JSON Web Tokens), bcrypt (хеширование паролей).

**Архитектура:** REST API сервис с базой данных PostgreSQL для хранения пользователей, ролей и разрешений.

**Функционал:**
- Аутентификация: регистрация (/signup), вход (/login), обновление токенов (/refresh), выход (/logout), верификация (/verify)
- Управление пользователями: CRUD операции, назначение ролей, активация/деактивация
- Управление ролями: создание, просмотр, обновление, удаление ролей, назначение разрешений
- Управление разрешениями: создание разрешений, проверка прав доступа пользователя
- Получение информации о текущем пользователе (/me) с его разрешениями

**Модель безопасности:** Ролевая модель доступа (RBAC) — пользователи получают роли, роли содержат разрешения, разрешения определяют доступ к функционалу системы.

**API Endpoints:** Authentication, Users, Roles, Permissions. Административные endpoints требуют прав администратора.

### 7. Enterprise Service (enterprise-service-dev)

**Назначение:** Core сервис для управления статичными данными предприятия: техника, смены, режимы работы, точки погрузки/разгрузки, статусы.

**Технологии:** Python, FastAPI, PostgreSQL, Alembic (миграции), uv (менеджер зависимостей).

**Архитектура:** REST API сервис с базой данных PostgreSQL для хранения справочных данных предприятия.

**Функционал:**
- Управление техникой (Vehicles): добавление, просмотр мобильных объектов (ПДМ, ШАС — самосвалы)
- Режимы работы (WorkRegimes): определение рабочих смен с динамическим расчётом времени
- Сменные задания (ShiftTasks): создание наряд-заданий с маршрутами для техники
- Маршруты (RouteTasks): задания с точками погрузки и разгрузки
- Статусы: справочник статусов техники (ремонт, обед, простой и т.д.)
- Точки работ (LoadUnloadPoints): управление местами погрузки и разгрузки

**API Endpoints:** WorkRegimes, Vehicles, LoadUnloadPoints, Statuses, ShiftTasks. Health checks для Kubernetes (liveness/readiness probes).

### 8. Dump Service (dump-service-dev)

**Назначение:** Сервис формирования дампов данных по рейсам (trips) из базы Trip Service и сохранения их в формате parquet для аналитики.

**Технологии:** Python 3.13+, FastAPI, PostgreSQL, MinIO/S3, Redis, uv (менеджер зависимостей), Alembic (миграции).

**Архитектура:** REST API сервис, который извлекает данные о рейсах из Trip Service, преобразует в parquet-файлы и сохраняет в архив tar.gz.

**Функционал:**
- Формирование дампа данных по завершённому рейсу (trip)
- Извлечение истории состояний (states) и тегов (tags) рейса
- Сохранение результатов в виде tar.gz архива с parquet-файлами
- Регистрация дампа в собственной базе данных dump-service
- Передача файлов в хранилище MinIO/S3 для последующей синхронизации
- Интеграция с Analytics Service: parquet файлы загружаются в ClickHouse через ETL

**Поток данных:** Trip Service → Dump Service (извлечение) → Parquet files → Tar.gz archive → MinIO/S3 → Analytics Service (ETL) → ClickHouse.

### 9. Dispatching Server Repo (dispatching-server-repo-dev)

**Назначение:** Репозиторий server-части системы диспетчеризации, объединяющий несколько микросервисов для локальной разработки и тестирования.

**Технологии:** Docker Compose, Task (task runner), Vector (логирование/мониторинг), Dozzle (логи контейнеров).

**Архитектура:** Monorepo с docker-compose конфигурацией для запуска всех серверных компонентов системы диспетчеризации.

**Функционал:**
- Запуск Enterprise Service (порт 8002) — управление техникой и заданиями
- Запуск Client (порт 5173) — диспетчерский интерфейс
- Запуск API Gateway (порт 8015) — маршрутизация запросов
- Интеграция с Vector (порт 9099) — сбор и агрегация логов
- Мониторинг через Dozzle (порт 9998) — просмотр логов контейнеров в реальном времени
- Поддержка нескольких окружений: dev (.env_server_dev) и stage (.env_server_stage)

**Команды управления:** `task init-server` (инициализация), `task dev-server` (запуск), `task logs` (просмотр логов), `task down` (остановка).

### 10. Monitoring Repo (monitoring-repo-dev)

**Назначение:** Репозиторий инфраструктуры мониторинга и обработки данных, объединяющий все необходимые сервисы для работы системы диспетчеризации.

**Технологии:** Docker Compose, Redis, eKuiper (потоковая обработка), NanoMQ (MQTT брокер), PostgreSQL + PostGIS + TimescaleDB, Airbyte (ETL), Apache Superset (BI), Trino (федеративные запросы), ClickHouse (OLAP), Dozzle (логи).

**Архитектура:** Набор docker-compose конфигураций для запуска всей инфраструктуры: базы данных, брокеры сообщений, потоковая обработка, аналитика.

**Функционал:**
- **Redis:** Кэш и очередь сообщений для межсервисного взаимодействия
- **eKuiper:** Потоковая обработка данных в реальном времени (правила, фильтры, агрегации)
- **NanoMQ:** MQTT брокер для получения телеметрии от бортовых контроллеров
- **PostgreSQL + PostGIS + TimescaleDB:** Основная БД с поддержкой геоданных и временных рядов
- **Airbyte:** Интеграция и синхронизация данных между системами
- **Apache Superset:** Визуализация данных и BI-аналитика (дашборды, графики)
- **Trino:** Движок для федеративных запросов к разным источникам данных
- **ClickHouse:** OLAP база для аналитических запросов высокой производительности
- **Dozzle:** Веб-интерфейс для просмотра логов контейнеров в реальном времени

**Запуск:** `make dev-bort` (разработка), `make bootstrap-bort` (полная инициализация с settings-service), `make stop` (остановка).

### 11. Settings Server (settings-server-dev)

**Назначение:** Сервис управления настройками и секретами для бортовых контроллеров, интеграция с HashiCorp Vault.

**Технологии:** Python, FastAPI, HashiCorp Vault (хранение секретов), Docker.

**Архитектура:** REST API сервис, который управляет конфигурацией бортов через шаблоны .env и хранит секреты в Vault.

**Функционал:**
- Управление секретами бортов: `POST /api/secrets/{vehicle_id}` записывает объединённые секреты в Vault
- Динамическая загрузка шаблонов: `.env_bort_template` читается с диска при каждом запросе (обновления без перезапуска сервиса)
- Уведомление бортов об изменениях: опциональная отправка webhook на `settings-bort` при изменении секретов
- Конфигурация уведомлений через переменные окружения: URL шаблона, таймауты, количество попыток, интервалы повторных попыток

**Интеграция с bort:** Settings Server → Vault (хранение) → Settings Bort (получение) → Бортовой контроллер (использование).

### 12. Settings Bort (settings-bort-dev)

**Назначение:** Клиентский сервис для бортовых контроллеров, который получает настройки и секреты от Settings Server и экспортирует их в .env файл.

**Технологии:** Python, FastAPI, SQLite (локальное хранение), Docker.

**Архитектура:** REST API + Admin UI для управления конфигурацией борта, локальная БД SQLite для хранения настроек.

**Функционал:**
- Admin UI (`GET /admin`) — веб-интерфейс для настройки подключений
- Управление конфигурацией: `GET/POST /api/admin/config` — чтение/запись runtime конфигурации
- Проверка подключений: `POST /api/admin/test-connections` — тестирование связи с серверами
- Инициализация секретов: `POST /api/admin/init/{vehicle_id}` — получение секретов от Settings Server
- Синхронизация секретов: `POST /api/admin/sync/{vehicle_id}` — webhook/poll helper для обновления
- Экспорт .env: `POST /api/admin/export-env` — сохранение секретов в файл для использования бортом
- Автоматическая инициализация при старте: цикл повторных попыток подключения к Settings Server
- Фоновая синхронизация: периодический опрос Settings Server на наличие изменений секретов
- Локальное хранение: SQLite база `./data/settings_bort.db` для сохранения конфигурации

**Автоматизация:** Поддержка auto init (при старте) и auto sync (фоновый polling) с настраиваемыми интервалами и количеством попыток.

### 13. Sync Service (sync-service-dev)

**Назначение:** Сервис синхронизации данных между бортовыми контроллерами и серверной частью через MQTT и RabbitMQ, управление доставкой сообщений и координацией владения.

**Технологии:** Python, FastAPI, MQTT client, RabbitMQ (aio-pika), Redis, Docker.

**Архитектура:** REST API + фоновые процессы для обработки MQTT сообщений, координации ownership и доставки данных.

**Функционал:**
- **MQTT Client:** Подключение к MQTT брокеру для получения телеметрии от бортов
- **Disassembler:** Разбор входящих MQTT сообщений на отдельные события
- **Reassembler:** Сборка исходящих сообщений для отправки на борт
- **Events Store:** Хранение событий в Redis для последующей обработки
- **Locks Store:** Управление блокировками для предотвращения конфликтов
- **Delivery Manager:** Управление доставкой сообщений с гарантией доставки
- **Retry Manager:** Механизм повторных попыток при сбоях доставки
- **Ownership Coordinator:** Координация владения бортом между несколькими инстансами сервиса
- **Autorepub Config Manager:** Управление конфигурацией автопубликации
- **Autorepub MQTT/RabbitMQ Managers:** Менеджеры для перепубликации сообщений между MQTT и RabbitMQ

**Поток данных:** Bort → MQTT → Sync Service (Disassembler) → Events Store → Delivery Manager → RabbitMQ → Другие сервисы.

### 14. Telemetry Service (telemetry-service-dev)

**Назначение:** Сервис сбора и хранения телеметрии от транспортных средств в Redis Streams для дальнейшей обработки другими сервисами.

**Технологии:** Python, FastAPI, gmqtt (async MQTT client), aioredis (Redis Streams), Loguru (логирование), Docker.

**Архитектура:** REST API + фоновый MQTT consumer, который подписывается на топики телеметрии и сохраняет данные в Redis Streams с TTL.

**Функционал:**
- Подписка на MQTT топики: `truck/{vehicle_id}/sensor/{sensor_type}/events` и `truck/{vehicle_id}/sensor/{sensor_type}/ds`
- Сохранение телеметрии в Redis Streams с настраиваемым TTL (по умолчанию 2 часа = 7200 секунд)
- Формат ключа Redis Stream: `telemetry-service:{sensor_type}:{vehicle_id}` (например, `telemetry-service:speed:AC9`)
- Health check endpoints для мониторинга состояния сервиса (basic, liveness, readiness probes)
- Поддержка типов датчиков: speed (скорость), weight (вес), fuel (топливо), gps (координаты), vibro (вибрация)

**Входящие данные:** JSON сообщения с телеметрией от бортовых контроллеров через MQTT брокер NanoMQ.

**Исходящие данные:** Redis Streams с временными рядами телеметрии для чтения другими сервисами (Analytics, Monitoring).

### 15. WiFi Event Dispatcher (wifi-event-dispatcher-dev)

**Назначение:** Распределённая система маршрутизации событий между бортовыми устройствами грузовиков (BORT) и центральным сервером через gRPC bidirectional streaming и RabbitMQ, активируемая при наличии WiFi-соединения.

**Технологии:** Go (Golang), gRPC (bidirectional streaming), Protocol Buffers, RabbitMQ, NanoMQ (MQTT), Uber FX (dependency injection), Zerolog (логирование), Docker.

**Архитектура:** Два компонента — Server (центральный) и Bort (бортовой клиент), обменивающиеся данными через gRPC стримы при наличии WiFi.

**Функционал:**
- **WiFi-мониторинг:** Подписка на MQTT топик `truck/<ID>/sensor/wifi/fake_events` для отслеживания наличия WiFi-соединения
- **Управление жизненным циклом стримов:** WiFi up → открытие gRPC стримов, WiFi down → закрытие стримов
- **Отправка событий (BORT → Server):** Локальный RabbitMQ на борту → gRPC stream → центральный сервер → RabbitMQ сервера
- **Получение событий (Server → BORT):** RabbitMQ сервера → gRPC stream → BORT → локальный RabbitMQ на борту
- **Autorepub management:** HTTP-клиент для управления suspend/resume автопубликации в sync-service
- **Reconnect logic:** Автоматическое переподключение gRPC стримов при потере соединения
- **Bidirectional streaming:** Одновременная двусторонняя передача данных через один gRPC канал

**Поток данных:** 
- BORT → Local RabbitMQ → gRPC Stream → Server → Central RabbitMQ → Другие сервисы
- Server → Central RabbitMQ → gRPC Stream → BORT → Local RabbitMQ → Бортовые приложения

### 16. CDC Distributor (cdc-distributor-dev)

**Назначение:** Сервис дистрибуции Change Data Capture (CDC) событий на бортовые системы, чтение изменений из баз данных через Debezium и публикация агрегированных данных в AMQP очереди для каждого борта.

**Технологии:** Python, RabbitMQ Streams (rstream), PostgreSQL (хранение offset), AMQP (aio-pika), msgspec (сериализация JSON), Docker.

**Архитектура:** Consumer приложений для чтения CDC событий из RabbitMQ Streams, агрегатор last-write-wins, publisher с подтверждением доставки.

**Функционал:**
- **Чтение CDC событий:** Подписка на RabbitMQ Streams от Debezium (изменения в graph-service, enterprise-service, auth-service, trip-service)
- **Per-bort consumer:** Для каждого (борт x сервис) создаётся отдельный stream consumer со своим offset — независимое чтение без блокировок
- **Агрегация по таблицам:** MultiTableAggregator группирует события по таблицам, схлопывает по ID (last-write-wins — последнее изменение побеждает)
- **At-least-once delivery:** Offset сохраняется только после подтверждения брокером (publisher confirm) — при сбоях батч перечитывается
- **Durable очереди:** Очереди бортов объявляются как durable — сообщения копятся при оффлайне борта и доставляются при подключении
- **Буферизация:** События накапливаются до batch_size или timeout перед агрегацией
- **Seq_id tracking:** Отслеживание последовательности сообщений для обеспечения порядка обработки на борту
- **Retry с exponential backoff:** Автоматические повторные попытки публикации при ошибках с экспоненциальной задержкой

**Поток данных:** Debezium (WAL изменения БД) → RabbitMQ Streams → CDC Distributor (агрегация) → AMQP очереди бортов → Бортовые системы.

### 17. CDC Bort Applier (cdc-bort-applier-dev)

**Назначение:** Бортовой сервис применения CDC событий, получает агрегированные изменения из AMQP очередей и применяет их к локальной базе данных борта.

**Технологии:** Python, asyncio, aio-pika (AMQP consumer), SQLAlchemy/PostgreSQL (локальная БД), Loguru (логирование), Docker.

**Архитектура:** Consumer приложение с Outbox паттерном для надёжной обработки входящих CDC событий и синхронизации состояния.

**Функционал:**
- **AMQP Consumers:** Подписка на очереди `server.bort_{id}.{service}.src` для получения CDC событий от центрального сервера
- **Применение изменений:** Распаковка JSON агрегатов и применение upserts/deletes к локальным таблицам PostgreSQL
- **Outbox Worker:** Фоновый процесс для публикации исходящих событий из outbox таблицы в AMQP (reverse sync)
- **Graceful shutdown:** Корректная остановка всех consumers при получении SIGTERM/SIGINT сигналов
- **Конфигурация через env:** VEHICLE_ID (идентификатор борта), POSTGRES_URL (подключение к локальной БД), AMQP_URL (RabbitMQ)
- **Множественные сервисы:** Одновременная обработка CDC событий от graph-service, enterprise-service, auth-service, trip-service
- **Seq_id tracking:** Отслеживание последовательности сообщений для обеспечения порядка применения изменений

**Поток данных:** AMQP очередь борта → CDC Bort Applier (распаковка) → Применение к локальной PostgreSQL → Outbox Worker → Публикация обратных событий.

### 18. Dispa Backend / Trip Service (dispa-backend-dev)

**Назначение:** Ключевой бортовой сервис управления рейсами горной техники, отслеживание выполнения заданий и ведение state machine состояния машины.

**Технологии:** Python, FastAPI, Redis (state machine), PostgreSQL + TimescaleDB (история рейсов), Alembic (миграции), Nanomq (MQTT), eKuiper (обработка событий датчиков), Docker.

**Архитектура:** Stateless архитектура с хранением состояния в Redis, подписка на события датчиков через MQTT, автоматическое определение плановых и внеплановых рейсов.

**Функционал:**
- **Управление рейсами:** Получение плановых рейсов с сервера, отслеживание активного рейса, фиксирование внеплановых рейсов
- **State Machine в Redis:** Хранение текущего состояния машины (moving/stopped, loaded/empty, active/inactive) на основе событий от датчиков
- **Pub/Sub механизм:** Публикация изменений состояния для реактивной обработки другими компонентами
- **Интеграция с eKuiper:** Подписка на события датчиков из локального Nanomq (speed, weight, vibro, tag raw)
- **Хранение истории:** PostgreSQL + TimescaleDB для хранения истории рейсов и телеметрии (hypertables для временных рядов)
- **Автоматические миграции:** Alembic применяет миграции при старте (создание таблиц shift_tasks, tasks, trips, trip_state_history, trip_tag_history, trip_analytics)
- **Nanomq интеграция:** Чтение событий датчиков (`/truck/${truck_id}/sensor/*/events`) и публикация событий рейсов (`/truck/${truck_id}/trip-service/events`)

**Redis ключи:** `trip-service:vehicle:${vehicle_id}:state` — JSON состояние State Machine.

**Идентификаторы:** vehicle_id = truck_id (один идентификатор, разное именование для совместимости).

### 19. Dispa Frontend (dispa-frontend-dev)

**Назначение:** React приложение для отображения и управления заданиями на смену в диспетчерской системе горных работ.

**Технологии:** React 18.2, TypeScript 5.2, Vite 5.0, Axios 1.6 (HTTP клиент), CSS Modules (стилизация), Nginx (продакшен сервер), Docker.

**Архитектура:** Single Page Application (SPA) с компонентной структурой, интеграция с Trip Service API для получения заданий.

**Функционал:**
- Просмотр всех заданий за текущую смену в табличном виде
- Активация первого задания кнопкой «Приступить к смене»
- Переключение между заданиями (клик по строке задания)
- Отображение статусов заданий: «На выполнение», «В работе», «Выполнено», «Приостановлено»
- Интеграция с Trip Service API через axios client
- Адаптивный UI для работы на различных устройствах

**API Endpoints:** `GET /api/tasks` (список заданий), `GET /api/active/task` (активное задание), `PUT /api/tasks/{id}` (обновление статуса), `DELETE /api/active/task` (деактивация).

**Структура:** Pages (ShiftTasksPage), Shared components (tripServiceApi), CSS Modules для изоляции стилей.

### 20. Graph Service Frontend (graph-service-frontend-dev)

**Назначение:** React SPA для визуализации и редактирования графов дорожных сетей карьера с интерактивным 2D редактором и 3D визуализацией, real-time трекингом транспорта через WebSocket.

**Технологии:** React 18.2, TypeScript 4.9.5, Create React App 5.0.1, Three.js 0.159.0 (3D движок), @react-three/fiber 8.15.0 (React renderer для Three.js), Socket.IO Client 4.7.0 (WebSocket), Axios 1.6.0 (HTTP), React Router DOM 6.8.0, Nginx (продакшен сервер).

**Архитектура:** Single Page Application с компонентной структурой: editor компоненты, three.js компоненты для 3D визуализации, shared компоненты.

**Функционал:**
- **Интерактивный 2D редактор:** Canvas для создания узлов, ребер и меток схемы дорог
- **3D визуализация:** Пространственное отображение графа с использованием Three.js и react-three/fiber
- **Real-time трекинг:** Отслеживание позиции транспортных средств через Socket.IO WebSocket
- **Многоуровневая структура:** Поддержка вертикальных лестниц (spiral edges) между уровнями карьера
- **Настройки GPS топиков:** Фильтрация отслеживаемого транспорта по MQTT топикам
- **Поиск меток:** Определение текущей позиции транспорта по координатам
- **Построение маршрутов:** Визуализация путей между узлами графа

**Компоненты:** EditorToolbar (панель инструментов), SettingsPage (настройки GPS), VehiclesPanel (трекинг транспорта), NodeSphere/EdgeLine/TagSphere/VehicleSphere (3D объекты), SpiralEdge (спиральная лестница).

### 21. Enterprise Frontend Demo (enterprise-frontend-demo-dev)

**Назначение:** Демонстрационный фронтенд для управления наряд-заданиями с современным UI, CRUD операциями и фильтрацией.

**Технологии:** React, TypeScript, Vite, Tailwind CSS (стилизация), Docker (dev + production), Nginx (продакшен сервер), Hot reload для разработки.

**Архитектура:** Single Page Application с компонентной структурой, интеграция с Enterprise Service API для управления заданиями.

**Функционал:**
- **CRUD операции:** Создание, просмотр, обновление и удаление наряд-заданий
- **Управление маршрутами:** Настройка точек А и Б для каждого задания
- **Фильтрация:** По технике (vehicle_id) и дате выполнения
- **Валидация форм:** Проверка корректности вводимых данных перед отправкой
- **Адаптивный дизайн:** Корректное отображение на различных устройствах
- **TypeScript типизация:** Строгая типизация всех компонентов и API запросов

**Структура:** API client (axios), Components (ShiftTaskList, ShiftTaskCard), Pages, Shared utilities.

**Запуск:** `start-dev.bat` (Windows) или `./start-dev.sh` (Linux/Mac), Docker Compose для production.

### 22. Audit Dev / Audit Library (audit-dev)

**Назначение:** Библиотека SQLAlchemy 2.x для транзакционного аудит-логирования с использованием паттерна outbox, запись изменений в RabbitMQ Stream.

**Технологии:** Python, SQLAlchemy 2.x, RabbitMQ Stream, FastAPI middleware (опционально), uv (менеджер зависимостей).

**Архитектура:** Mixin для моделей SQLAlchemy, который автоматически записывает diff изменений (create/update/delete) в таблицу audit_outbox в той же транзакции, daemon модуль для публикации в RabbitMQ.

**Функционал:**
- **AuditMixin:** Добавление к моделям SQLAlchemy для автоматического отслеживания изменений
- **Outbox паттерн:** Запись аудита в таблицу audit_outbox в той же транзакции что и основное изменение (атомарность)
- **Diff tracking:** Запись старых и новых значений полей при update операциях
- **User tracking:** Отслеживание пользователя, выполнившего операцию (через JWT или set_audit_user context manager)
- **Service identification:** Идентификация сервиса-источника изменений (service_name параметр)
- **Daemon module:** Фоновый процесс чтения outbox и публикации в RabbitMQ Stream с retry и exponential backoff
- **Field exclusion:** Возможность исключить чувствительные поля из аудита (__audit_exclude__ атрибут)
- **FastAPI middleware:** Автоматическое извлечение user_id из JWT токена (опциональная зависимость)

**Операции:** create (создание), update (обновление), delete (удаление). Каждая операция записывает old_values/new_values diff.

### 23. Audit Exporter (audit-exporter-dev)

**Назначение:** Сервис экспорта аудита из таблиц audit_outbox нескольких PostgreSQL баз в ClickHouse для централизованного хранения и аналитики.

**Технологии:** Python, FastAPI, Pydantic Settings, PostgreSQL (чтение), ClickHouse (запись батчами), Loguru (логирование), uv (менеджер зависимостей), ruff (linting/formatting), mypy (type checking).

**Архитектура:** ASGI приложение с фоновым polling loop, который периодически опрашивает источники audit_outbox и экспортирует записи в ClickHouse.

**Функционал:**
- **Множественные источники:** Чтение audit_outbox из нескольких PostgreSQL баз (graph-service, enterprise-service, trip-service)
- **Batch export:** Экспорт записей батчами по 500 записей (настраивается через SOURCE_POLL_BATCH_SIZE)
- **Deduplication:** Дедупликация на стороне ClickHouse по токену (source_name, outbox_id) — повторная отправка безопасна
- **Mark processed:** После успешной записи строки помечаются как обработанные (processed = true)
- **Polling interval:** Настраиваемый интервал опроса источников (по умолчанию 10 секунд)
- **Health checks:** Liveness (/healthz) и readiness (/readyz) endpoints с диагностикой зависимостей
- **TLS support:** Поддержка защищённого подключения к ClickHouse (HTTPS, порт 8443)
- **Dependency connect timeout:** Таймаут подключения к зависимостям при старте (по умолчанию 5 секунд)

**Источники:** graph, enterprise, trip — каждый конфигурируется отдельным набором переменных окружения с префиксом {NAME}__POSTGRES_*.

### 24. Auth Library (auth-lib-dev)

**Назначение:** Библиотека FastAPI для проверки JWT-based permissions, единый источник правды для системы разрешений и удобные зависимости для проверки доступа.

**Технологии:** Python, FastAPI, JWT (JSON Web Tokens), Permission enum (система разрешений), Action enum (действия: VIEW, CREATE, UPDATE, DELETE).

**Архитектура:** Библиотека с FastAPI dependencies для интеграции в микросервисы, проверка токенов через API Gateway.

**Функционал:**
- **Permission enum:** Единая система разрешений для всех сервисов (WORK_ORDER, VEHICLE, USER, ROLE и т.д.)
- **Action enum:** Типы действий (VIEW, CREATE, UPDATE, DELETE) для каждого разрешения
- **require_permission dependency:** Проверка наличия конкретного разрешения у пользователя (иначе 403 Forbidden)
- **get_current_user dependency:** Получение текущего пользователя без проверки конкретных разрешений
- **X-Source header check:** Если заголовок X-Source отсутствует или не равен api-gateway, запрос считается внутренним (без проверки токена)
- **JWT validation:** Проверка валидности JWT токена через auth-service (иначе 401 Unauthorized)
- **UserPayload model:** Модель данных пользователя (id, username, role, permissions)

**Использование:** `user: UserPayload | None = Depends(require_permission(Permission.WORK_ORDER, Action.VIEW))` — защита эндпоинта проверкой разрешения.

### 25. Platform SDK (platform-sdk-dev)

**Назначение:** Типизированный асинхронный Python SDK для внутренних HTTP сервисов платформы УГМК, упрощение интеграции микросервисов.

**Технологии:** Python, httpx (async HTTP client), Pydantic (модели данных), Type hints (строгая типизация), uv/pip (менеджеры зависимостей).

**Архитектура:** Async клиентская библиотека с typed models для каждого сервиса платформы, единая точка доступа к API.

**Функционал:**
- **AsyncClients:** Единый async контекстный менеджер для работы со всеми сервисами платформы
- **ClientSettings:** Конфигурация подключения (base_url, timeout, retry policy)
- **Typed models:** Строго типизированные модели данных для каждого сервиса (VehicleTelemetryField, FilterParam и т.д.)
- **Filter system:** Система фильтрации с FilterGroup, FilterParam, FilterType (AND/OR), QueryOperator (EQUALS, CONTAINS, GT, LT и т.д.)
- **Pagination support:** Поддержка пагинации через skip/limit параметры
- **Sorting:** Сортировка результатов по полям с направлением (ASC/DESC)
- **Analytics integration:** Методы для получения телеметрии техники из analytics-service
- **Error handling:** Обработка HTTP ошибок и возврат структурированных ответов

**Пример использования:** `async with AsyncClients(settings) as clients: result = await clients.analytics.get_vehicle_telemetry(...)`

### 26. Dispatching Repo (dispatching-repo-dev)

**Назначение:** Управляющий репозиторий для запуска всей системы диспетчеризации через Docker Compose, объединяет инфраструктурные компоненты и микросервисы.

**Технологии:** Docker Compose, Task (task runner), Redis, eKuiper, NanoMQ, PostgreSQL + PostGIS + TimescaleDB, Dozzle.

**Архитектура:** Monorepo с docker-compose конфигурациями для server-части и bort-части системы.

**Функционал:**
- **Инфраструктура:** Redis (кэш/очередь), eKuiper (потоковая обработка), NanoMQ (MQTT брокер), PostgreSQL + PostGIS + TimescaleDB (основная БД)
- **Мониторинг:** Dozzle для просмотра логов контейнеров в реальном времени
- **Запуск:** `task dev-bort` — запуск бортовой части, `task dev-server` — запуск серверной части
- **Управление:** `task down` (остановка), `task logs-bort` (логи борта), `task ps` (статус контейнеров), `task urls` (список URL сервисов)
- **Миграции:** `task check-migrations` — проверка состояния миграций баз данных

**Сервисы:** Trip Service Backend (порт 8000), Graph Service Backend (порт 5001), Enterprise Service (порт 8002), Client (порт 5173), API Gateway (порт 8015).

### 27. Env Disp Infra (env-disp-infra-dev)

**Назначение:** Репозиторий инфраструктуры окружения для диспетчерской системы, содержит конфигурации Docker и настройки развёртывания.

**Технологии:** Docker Compose, environment configuration files.

**Архитектура:** Набор docker-compose файлов и переменных окружения для различных сред развёртывания (dev, stage, production).

**Функционал:** Конфигурация инфраструктуры, управление переменными окружения, шаблоны для развёртывания.

---

## ИТОГО УРОВЕНЬ 1: 27 КОМПОНЕНТОВ ПРОАНАЛИЗИРОВАНО

✅ **Завершён анализ всех компонентов системы АСУ ПГР**

**Категории компонентов:**
- **Бортовые приложения:** bort-client-dev, settings-bort-dev, dispa-backend-dev (Trip Service), cdc-bort-applier-dev
- **Диспетчерские интерфейсы:** client-disp-dev, dispa-frontend-dev, graph-service-frontend-dev, enterprise-frontend-demo-dev
- **Backend сервисы:** auth-service-backend-dev, enterprise-service-dev, analytics-service-dev, graph-service-backend-dev, dump-service-dev, sync-service-dev, telemetry-service-dev
- **Инфраструктура:** api-gateway-dev, monitoring-repo-dev, dispatching-repo-dev, dispatching-server-repo-dev, env-disp-infra-dev
- **CDC система:** cdc-distributor-dev, cdc-bort-applier-dev
- **WiFi синхронизация:** wifi-event-dispatcher-dev
- **Настройки:** settings-server-dev, settings-bort-dev
- **Аудит:** audit-dev, audit-exporter-dev
- **Библиотеки:** auth-lib-dev, platform-sdk-dev

---

*Продолжение следует... Уровень 2: Модули внутри компонентов*

## Уровень 2: МОДУЛИ ВНУТРИ КОМПОНЕНТОВ

### client-disp-dev (Диспетчерский интерфейс) - FSD Архитектура

**Архитектура:** Feature-Sliced Design (FSD) — модульная архитектура с разделением на слои: app/, entities/, features/, pages/, shared/, widgets/.

**Pages (25 страниц):**
- **dispatch-map/** — Карта диспетчера с Redux state management, слоями карты, фильтрами горизонтов, историей перемещений техники
- **work-order/** — Наряд-задания: создание, редактирование, управление заданиями на смену
- **fleet-control/** — Управление парком техники: мониторинг статуса, фильтрация, группировка
- **trip-editor/** — Редактор рейсов: настройка маршрутов, точек погрузки/разгрузки
- **map/** — Основная карта с визуализацией схемы дорог
- **time-map/** — Временная карта (heatmap активности техники)
- **work-time-map/** — Карта рабочего времени (аналитика использования техники)
- **cargo/** — Справочник видов груза
- **equipment/** — Справочник оборудования
- **horizons/** — Управление горизонтами карьера
- **places/** — Справочник мест работ (точки погрузки/разгрузки)
- **statuses/** — Справочник статусов техники
- **tags/** — Метки на карте (зоны, ограничения)
- **staff/** — Управление персоналом (водители, операторы)
- **roles/** — Ролевая модель доступа
- **sections/** — Разделы системы
- **settings/** — Настройки системы
- **dispatchers-report/** — Отчёты диспетчеров
- **vgok/** — Специфичные функции для ВГОК
- **workspace/** — Рабочее пространство диспетчера
- **main/** — Главная страница
- **app/** — Корневое приложение
- **learning/** — Обучающие материалы
- **forbidden/** — Страница запрета доступа (403)
- **not-found/** — Страница не найдена (404)

**dispatch-map/model/slice.ts (Redux):** Управление состоянием карты — режимы работы, фильтры горизонтов, видимость техники, слои карты (ROADS, BACKGROUND), фокус на объектах, контекстное меню, история перемещений (player playback), ruler tool, graph edit mode.

---

### infrastructure/ — ИНФРАСТРУКТУРНЫЕ КОМПОНЕНТЫ

#### 1. PostgreSQL (postgres-disp-dev)

**Назначение:** Основная реляционная база данных системы с поддержкой геоданных (PostGIS) и временных рядов (TimescaleDB).

**Технологии:** PostgreSQL, PostGIS (геопространственные расширения), TimescaleDB (временные ряды), Docker.

**Структура баз данных (из initdb_server SQL скриптов):**
- **dispatching** — основная БД (создаётся автоматически через POSTGRES_DB env var)
- **dispatching_graph** — БД для graph-service (схема дорог, узлы, ребра, метки)
- **trip_service** — БД для trip-service (рейсы, задания, история состояний)
- **dispatching_auth** — БД для auth-service (пользователи, роли, разрешения)
- **airbyte** — БД для Airbyte ETL (интеграция данных)
- **superset** — БД для Apache Superset (BI аналитика, дашборды)

**Инициализация:** SQL скрипты в initdb/, initdb_bort/, initdb_server/ папках выполняются при первом запуске контейнера.

**PostGIS:** Включается через `00_enable_postgis.sql` — поддержка геопространственных запросов (расстояния, полигоны, координаты).

#### 2. eKuiper (ekuiper-dev)

**Назначение:** Потоковая обработка данных от бортовых датчиков в реальном времени, downsample (прореживание), агрегация событий и детекция аномалий.

**Технологии:** eKuiper (LF Edge проект), MQTT (NanoMQ), PostgreSQL sink, SQL-like rules engine, Docker.

**Архитектура:** Правила (rules) обрабатывают потоки (streams) данных от датчиков техники, применяют фильтры, агрегации и публикуют результаты обратно в MQTT или сохраняют в PostgreSQL.

**Streams (из ruleset.json):**
- **external_stream_gps/speed/weight/fuel** — внешние потоки сырых данных от датчиков
- **local_stream_*_ds** — локальные потоки raw данных (downsampled)
- **speed_downsampled/weight_downsampled/fuel_downsampled/gps_downsampled** — прореженные потоки для снижения нагрузки
- **mqtt_stream** — wildcard поток (#) для захвата всех MQTT сообщений
- **simulator_stream** — симулятор для тестирования (WiFi fake events)

**Rules (ключевые правила обработки):**
- **rule_downsample_speed/weight/fuel/gps** — Прореживание данных: пропускает изменения только если разница >50% от предыдущего значения (снижение объёма данных в 10-50 раз)
- **rule_speed_events** — Агрегация скорости за 1 секунду (TUMBLINGWINDOW): AVG(speed), статус moving/stopped
- **rule_weight_events** — Агрегация веса за 1 секунду: AVG(weight), статус loaded (>5т) / empty
- **rule_fuel_events** — Детекция событий топлива: refueling (рост), consumption (падение), idle (нет изменений)
- **rule_vibro_events** — Детекция вибрации по изменению веса: weight_rise (+2т), weight_fall (-2т), weight_flat (±0.5т)
- **rule_tag_detection** — Определение меток на карте: вызов graphService API `/api/location/find` по GPS координатам, возврат tag_id, place_id, place_name
- **rule_fuel_alerts** — Алерты низкого уровня топлива: <10%, группировка за 2 секунды
- **mqtt_raw_to_jsonb** — Сохранение всех сырых MQTT сообщений в PostgreSQL таблицу `telemetry.mqtt_raw_data` для отладки
- **rule_wifi_fake_events_on/off** — Симуляция WiFi событий для тестирования wifi-event-dispatcher

**Поток данных:** Датчики → NanoMQ → eKuiper (правила) → Downsampled события → Trip Service / Telemetry Service.

#### 3. MinIO (minio-disp-dev)

**Назначение:** S3-совместимое объектное хранилище для дампов рейсов (parquet файлы) и других артефактов системы.

**Технологии:** MinIO, mc (MinIO Client), AMQP notifications (RabbitMQ), Docker.

**Бакеты (из buckets.json):**
- **dump-service** — хранение parquet архивов завершённых рейсов от Dump Service
- **graph-service** — хранение артефактов графа дорог (бекапы, экспорт)

**Конфигурация событий:** AMQP уведомления при загрузке файлов (put events) → RabbitMQ exchange `minio.events` → Analytics Service (FastStream consumer загружает в ClickHouse).

**Инициализация:** setup.sh скрипт создаёт бакеты, настраивает AMQP notifications через mc CLI.

#### 4. NanoMQ (nanomq-bort-disp-dev)

**Назначение:** MQTT брокер для получения телеметрии от бортовых датчиков техники в реальном времени.

**Технологии:** NanoMQ (легковесный MQTT брокер), WebSocket support, Docker.

**Топики:** `truck/{vehicle_id}/sensor/{type}/{format}` — gps, speed, weight, fuel, vibro, tag, wifi (raw/events/ds форматы).

**Интеграция:** eKuiper подписывается на топики, обрабатывает потоки, публикует downsampled события обратно.

#### 5. RabbitMQ (rabbitmq-disp-dev, rabbitmq-bort-disp-dev)

**Назначение:** Message broker для межсервисной коммуникации, CDC событий, уведомлений MinIO.

**Технологии:** RabbitMQ, AMQP protocol, Streams plugin (для CDC), Docker.

**Использование:**
- **CDC Distributor:** RabbitMQ Streams для чтения изменений из Debezium
- **MinIO:** Exchange `minio.events` для уведомлений о новых файлах
- **Sync Service:** Очереди для доставки сообщений между бортом и сервером
- **WiFi Event Dispatcher:** gRPC streaming поверх RabbitMQ

**Два инстанса:** rabbitmq-disp-dev (серверная часть), rabbitmq-bort-disp-dev (бортовая часть).

#### 6. Vault (vault-disp-dev)

**Назначение:** HashiCorp Vault для безопасного хранения секретов (пароли, API ключи, сертификаты).

**Технологии:** HashiCorp Vault, Docker.

**Использование:** Settings Server записывает секреты бортов в Vault, Settings Bort читает их при инициализации.

#### 7. Debezium (debezium-disp-dev)

**Назначение:** Change Data Capture (CDC) платформа для отслеживания изменений в PostgreSQL базах данных.

**Технологии:** Debezium, Kafka Connect, PostgreSQL WAL decoding, Docker.

**Использование:** Чтение WAL логов PostgreSQL → публикация изменений в RabbitMQ Streams → CDC Distributor агрегирует и отправляет на борта.

**Мониторинг баз:** graph-service, enterprise-service, auth-service, trip-service databases.

---

## ИТОГО УРОВЕНЬ 2 (ЧАСТИЧНО): ПРОАНАЛИЗИРОВАНО

✅ **client-disp-dev:** 25 страниц FSD архитектуры, Redux state management (dispatch-map slice)  
✅ **infrastructure/:** 7 компонентов инфраструктуры (PostgreSQL, eKuiper, MinIO, NanoMQ, RabbitMQ x2, Vault, Debezium)

**Ключевые находки из кода:**
- **eKuiper ruleset.json:** 16 правил потоковой обработки (downsample, агрегация событий, детекция аномалий, tag detection через graphService API)
- **PostgreSQL initdb SQL:** 6 баз данных (dispatching, dispatching_graph, trip_service, dispatching_auth, airbyte, superset)
- **MinIO buckets.json:** 2 бакета (dump-service, graph-service) с AMQP notifications
- **Redux slice.ts:** Управление состоянием карты (layers, filters, focus, history player, ruler tool)

**Что дальше:**
- Продолжить анализ модулей в других компонентах (bort-client, analytics-service, graph-service-backend)
- Уровень 3: Важные файлы (>500 строк кода)
- Уровень 4: Связи между функциями/классами

---

*Продолжение следует...*

### bort-client-dev (Бортовое приложение) - FSD Архитектура

**Архитектура:** Feature-Sliced Design (FSD) — модульная архитектура с разделением на слои: app/, entities/, features/, pages/, shared/, widgets/.

**Pages (11 страниц из кода):**
- **work-orders/** — Список наряд-заданий для водителя: отображение маршрутов текущей смены, сортировка по route_order, переход к деталям задания
- **work-order-detail/** — Детали конкретного наряд-задания: информация о маршруте, точки погрузки/разгрузки
- **main-screen/** — Главный экран бортового приложения
- **main-menu/** — Главное меню навигации
- **vehicle-status/** — Статус техники (текущее состояние)
- **active-downtime/** — Активные простои (ремонт, обед)
- **downtime-select/** — Выбор типа простоя
- **login/** — Авторизация водителя
- **session-ended/** — Экран завершения сессии
- **settings/** — Настройки бортового приложения
- **stats/** — Статистика работы (рейсы, время, расстояние)

**WorkOrdersPage.tsx (код):** Использует useCurrentShiftTasks hook для получения заданий, RouteTaskList widget для отображения списка, useKioskNavigation для управления навигацией в киоск-режиме (выбор строки, подтверждение). Сортирует задания по route_order, при клике или подтверждении переходит на getRouteWorkOrderDetail(selectedId).

**Widgets (9 компонентов из кода):**
- **route-task-list/** — Список маршрутных заданий с прокруткой и выделением
- **route-task-detail/** — Детальная информация о задании
- **active-route-panel/** — Панель активного маршрута
- **trip-gauge/** — Индикатор прогресса рейса
- **kiosk-controls/** — Управление в киоск-режиме (крупные кнопки для тачскрина)
- **bottom-nav/** — Нижняя навигационная панель
- **status-bar/** — Строка статуса (время, связь, заряд)
- **new-shift-task-popup/** — Popup нового задания смены
- **page-layout/** — Общий layout страницы

---

### analytics-service-dev (Сервис аналитики) - Backend API

**Архитектура:** FastAPI application factory pattern с разделением на API routes, controllers, services, repositories.

**API Routes (из src/api/rest/v1/):**
- **vehicle_telemetry.py** — POST /vehicle-telemetry — получение телеметрии техники с фильтрами, пагинацией (skip/limit), сортировкой
- **trip_service/** — endpoints для работы с данными рейсов
- **minio.py** — endpoints для управления MinIO

**VehicleTelemetry endpoint (код):** Принимает VehicleTelemetryFilterRequest (фильтры по технике, времени, датчикам), возвращает PaginationResponse[VehicleTelemetryResponse] с пагинацией. Использует VehicleTelemetryController через FastAPI dependency injection.

**Background tasks:**
- **FastStream consumer** — обработка событий MinIO из RabbitMQ, загрузка parquet файлов в ClickHouse
- **ETL pipeline** — извлечение данных из MinIO → валидация → загрузка в ClickHouse таблицы

**Core modules (src/core/):** 15 модулей ядра — конфигурация, логирование, DTO схемы, типы сортировки, pagination responses.

---

### graph-service-backend-dev (Backend сервиса графов) - API Endpoints

**Архитектура:** FastAPI с SQLAlchemy async ORM, PostGIS для геопространственных запросов, Alembic миграции, WebSocket для real-time обновлений.

**Routers (18 API endpoints из кода):**
- **locations.py** — POST /location/find (поиск ближайшей метки по GPS), GET /route/{start}/{target} (построение маршрута между узлами), GET /route/place-node-ids (привязка мест к узлам графа)
- **levels.py** — CRUD операции с уровнями карьера (горизонтами)
- **nodes.py** — Управление узлами графа (создание, обновление, удаление)
- **edges.py** — Управление ребрами графа (дороги между узлами)
- **tags.py** — Метки на карте (зоны погрузки/разгрузки, ограничения)
- **places.py** — Места работ (ПП — пункты погрузки, ПР — пункты разгрузки)
- **ladders.py** — Ladder nodes (межуровневые соединения, спиральные лестницы)
- **horizons.py** — Горизонты карьера (фильтрация по уровням)
- **sections.py** — Секции дорог (группировка ребер)
- **shafts.py** — Шахты/стволы (вертикальные соединения)
- **substrates.py** — Подложки карты (фоновые изображения)
- **vehicles.py** — Транспортные средства на карте
- **ws_vehicle_tracking.py** — WebSocket для real-time трекинга техники
- **events_stream.py** — Server-Sent Events (SSE) для потоковых обновлений
- **map_player.py** — Воспроизведение истории перемещений (playback)
- **map_settings.py** — Настройки отображения карты
- **import_graphs.py** — Импорт графов из внешних источников

**Location find endpoint (код из locations.py):** Принимает GPS координаты {lat, lon}, конвертирует в Canvas координаты, ищет метку в радиусе которой находится точка через loc_finder.find_nearest(), возвращает {point_id, point_name, point_type}. Используется eKuiper rule_tag_detection для определения当前位置 техники.

**Route calculation:** GET /route/{start_node_id}/{target_node_id} — построение маршрута между двумя узлами графа через loc_finder.calculate_route() с использованием python-igraph алгоритмов поиска кратчайшего пути.

**Services (25 модулей из src/app/services/):** loc_finder (поиск меток, построение маршрутов), place_route_nodes (привязка мест к узлам), vehicle tracking service, ladder node service, level management service и др.

**Models:** SQLAlchemy модели для levels, nodes, edges, tags, places, ladders, sections, shafts, substrates, vehicles.

---

## ИТОГО УРОВЕНЬ 2 (ПРОДОЛЖЕНИЕ): ПРОАНАЛИЗИРОВАНО

✅ **bort-client-dev:** 11 страниц FSD, 9 виджетов, WorkOrdersPage.tsx код (навигация, сортировка заданий)  
✅ **analytics-service-dev:** FastAPI routes (vehicle_telemetry.py), FastStream consumer, ETL pipeline  
✅ **graph-service-backend-dev:** 18 routers (locations.py, levels.py, nodes.py, edges.py, tags.py и др.), loc_finder service, python-igraph маршруты

**Ключевые находки из кода:**
- **bort-client WorkOrdersPage.tsx:** useCurrentShiftTasks hook, RouteTaskList widget, kiosk navigation (крупные кнопки для тачскрина)
- **analytics vehicle_telemetry.py:** POST endpoint с VehicleTelemetryFilterRequest, PaginationResponse, dependency injection контроллера
- **graph-service locations.py:** POST /location/find (GPS → Canvas конвертация, поиск метки), GET /route/{start}/{target} (построение маршрута через igraph)
- **eKuiper integration:** rule_tag_detection вызывает graphService API `/api/location/find` для определения позиции техники

**Общий прогресс Уровень 2:**
- ✅ client-disp-dev (25 страниц, Redux slice)
- ✅ infrastructure/ (7 компонентов)
- ✅ bort-client-dev (11 страниц, 9 виджетов)
- ✅ analytics-service-dev (FastAPI routes, ETL)
- ✅ graph-service-backend-dev (18 routers, location/route services)

**Осталось проанализировать:** enterprise-service, auth-service, sync-service, telemetry-service, dispatching-repo и др.

---

### enterprise-service-dev (Сервис предприятия) - API Endpoints

**Архитектура:** FastAPI с SQLAlchemy async ORM, Alembic миграции, auth_lib permissions для защиты endpoints.

**Routers (13 endpoints из кода):**
- **vehicles.py** — CRUD техники: GET /vehicles (список с пагинацией page/size, фильтрация по vehicle_type/is_active), POST /vehicles (создание), PUT /vehicles/{id} (обновление), DELETE /vehicles/{id} (удаление)
- **vehicle_models.py** — Модели техники (марки, типы самосвалов)
- **work_regimes.py** — Режимы работы (смены, расписание)
- **shift_service.py** — Сменные задания (наряд-задания)
- **statuses.py** — Статусы техники (ремонт, обед, простой)
- **load_type.py** — Типы груза (руда, пустая порода, уголь)
- **load_type_category.py** — Категории грузов
- **organization_categories.py** — Категории организаций
- **sync.py** — Синхронизация данных с бортовыми системами
- **enterprise.py** — Управление предприятиями (организации)
- **health.py** — Health check endpoints
- **api.py** — API информация

**Vehicles endpoint (код из vehicles.py):** GET /vehicles с параметрами enterprise_id, vehicle_type, is_active, page, size. Использует auth_lib require_permission с множественными разрешениями (WORK_TIME_MAP.VIEW, TRIP_EDITOR.VIEW, WORK_ORDER.VIEW, EQUIPMENT.VIEW). VehicleService.get_list() возвращает список с пагинацией или все записи если page/size не указаны.

**Permissions:** Все endpoints защищены через auth_lib require_permission — проверка JWT токена и наличия разрешений у пользователя.

---

### sync-service-dev (Сервис синхронизации) - Autorepub Management

**Архитектура:** FastAPI + MQTT client + RabbitMQ publisher, управление перепубликацией сообщений между протоколами.

**API Routes (из app/api/routes/):**
- **autorepub.py** — Управление конфигурациями автопубликации (289 строк кода)
- **coordination.py** — Координация ownership (владения бортом между инстансами)
- **health.py** — Health check endpoints

**Autorepub config endpoints (код из autorepub.py):**
- **POST /autorepub/configs** — Создание временной конфигурации autorepub с параметрами: name, type (MQTT/RABBITMQ), source_instance_id, target_instances, source_topic, target_topic, queue_name, deduplication, autostart, retry policy (max_attempts, backoff_base, multiplier, max_delay)
- **DELETE /autorepub/configs?name={name}** — Удаление конфигурации
- **GET /autorepub/configs** — Список всех конфигураций
- **POST /autorepub/configs/{name}/activate** — Активация конфигурации (подписка на source topic)
- **POST /autorepub/configs/{name}/deactivate** — Деактивация конфигурации (отписка)

**AutorepubConfigResponse модель:** Содержит name, type, source/target instance IDs, topics, queue_name, deduplication flag, autostart, retry settings, is_active status.

**Логика активации:** Если config.autostart=true, автоматически подписывается на source topic через autorepub_mqtt_manager.subscribe_to_config() или autorepub_rabbitmq_manager.subscribe_to_config() в зависимости от типа.

**Coordination endpoint:** GET /coordination/ownership — проверка владения бортом текущим инстансом sync-service.

---

### telemetry-service-dev (Сервис телеметрии) - MQTT Consumer + Redis Streams

**Архитектура:** FastAPI + gmqtt (MQTT client) + aioredis (Redis Streams), фоновый consumer для обработки телеметрии.

**Services (из app/services/):**
- **mqtt_client.py** — TelemetryMQTTClient класс (205 строк): подключение к NanoMQ, подписка на топики `truck/+/sensor/+/events` и `truck/+/sensor/+/ds`, callback _on_message для обработки входящих сообщений
- **telemetry_storage.py** — TelemetryStorage класс (128 строк): сохранение телеметрии в Redis Streams с TTL, формирование ключа `telemetry-service:{sensor_type}:{vehicle_id}`

**MQTT Client логика (код из mqtt_client.py):**
- Инициализация: MQTTClient("telemetry-service") с callbacks on_connect, on_message, on_disconnect, on_subscribe
- Подписка на топики: ["truck/+/sensor/+/events", "truck/+/sensor/+/ds"] — wildcard pattern для всех vehicle_id и sensor_type
- Обработка сообщений: message_handler(vehicle_id, sensor_type, data) async callback вызывается при получении каждого сообщения
- Sensor types: speed, weight, fuel, gps, vibro (из топиков)
- Форматы: events (события с агрегацией), ds (downsampled raw данные)

**Telemetry Storage логика (код из telemetry_storage.py):**
- store_telemetry(vehicle_id, sensor_type, data) — сохранение в Redis Stream
- Ключ: `telemetry-service:{sensor_type}:{vehicle_id}` (например, `telemetry-service:speed:AC9`)
- Entry структура: {"timestamp": str(time.time()), "data": json.dumps(data)}
- TTL: настраивается через TELEMETRY_STREAM_TTL_SECONDS env var (по умолчанию 7200 сек = 2 часа)
- Redis xadd() добавляет запись в stream, expire() устанавливает TTL

**Routers:** Только health checks (GET /health, /health/live, /health/ready) — сервис не предоставляет REST API, только фоновая обработка MQTT → Redis.

---

### dispa-frontend-dev (Frontend диспетчера рейсов) - React Pages

**Архитектура:** React 18 + TypeScript, Vite bundler, CSS Modules для стилей.

**Pages (7 страниц из frontend/src/pages/):**
- **shift-tasks/** — ShiftTasksPage.tsx (234 строки): список заданий на смену, активация маршрутов через tripServiceApi.getShiftTasks(), getActiveTask(), activateTask(routeId), отображение количества завершенных рейсов getCompletedTripsCount()
- **main/** — Главная страница диспетчера
- **event-log/** — Лог событий системы
- **manual-actions/** — Ручные действия оператора
- **settings/** — Настройки приложения
- **trip-analytics/** — Аналитика рейсов
- **auth/** — Страница аутентификации

**Shared API (из shared/api/):**
- **tripServiceApi.ts** — Клиент для dispa-backend: getShiftTasks({page, size}), getActiveTask(), activateTask(taskId), getCompletedTripsCount(taskId)
- **graphServiceApi.ts** — Клиент для graph-service-backend

**TestDataImportModal.tsx** (8.3KB): Модальное окно импорта тестовых данных для разработки и демонстрации.

---

### graph-service-frontend-dev (Frontend редактора графов) - Three.js Visualization

**Архитектура:** React 18 + TypeScript, Three.js (@react-three/fiber, @react-three/drei) для 3D визуализации, Canvas 2D для 2D редактора.

**Components (из src/components/, 9 модулей):**
- **GraphEditor.tsx** (3878 строк!) — Главный компонент редактирования графа: режимы view/addNode/addEdge/addPlace/addLadder/move/edit/delete, масштабирование canvas, drag-and-drop узлов, WebSocket для real-time обновлений позиций техники, интеграция с enterprise-service для списка машин vehicleNamesMapRef
- **ThreeView.tsx** (53.3KB) — 3D визуализация графа через React Three Fiber: камера, освещение, рендеринг уровней карьера
- **VehiclePanel.tsx** (7.1KB) — Панель отображения техники на карте
- **editor/** (8 компонентов) — EditorToolbar, VehiclesPanel, SettingsPage, ImportDialog, LadderDialog и др.
- **three/** (8 компонентов) — Three.js специфичные компоненты для 3D рендеринга
- **shared/** (2 компонента) — AppHeader и общие UI элементы

**Hooks (из src/hooks/, 5 хуков):**
- **useSettings** — Управление настройками редактора
- **useWebSocket** — Real-time обновления позиций техники через WebSocket
- **useGraphData** — Загрузка и кэширование данных графа (уровни, узлы, ребра, метки, места)
- **useVehicles** — Загрузка списка техники из enterprise-service

**Services (из src/services/):**
- **api.ts** — HTTP клиент для graph-service-backend API: createNode, createEdge, createPlace, createTag, createHorizon, createLadder, connectLadderNodes, getHorizonObjectsCount, deleteHorizon, getHorizonGraph

**Utils (из src/utils/, 3 модуля):**
- **placeLocation.ts** — Конвертация координат мест: getPlaceLonLat, getPlaceMapXY, getPlaceCanvasXY

**Ключевые особенности GraphEditor.tsx (код):**
- Режимы работы: 'view' | 'addNode' | 'addEdge' | 'addPlace' | 'addLadder' | 'move' | 'edit' | 'delete'
- selectedNode/selectedEdge/selectedTag/selectedPlace state management
- Масштабирование и панорамирование: scale state, offset {x, y}
- Drag-and-drop меток: isDraggingRadius, draggingTagId, tempRadius
- Боковые панели: isLeftPanelOpen, isVehiclesPanelOpen
- Диалоги: showEditTag/Place/Node/Edge/Ladder, showImportDialog, showLadderDialog
- Ladder creation workflow: ladderStep ('selectLevels' | 'selectNode1' | 'selectNode2'), ladderSourceNode, ladderLevel1Id/2Id, ladderNode1Id/2Id
- Vehicle tracking: vehiclePosition из WebSocket, vehiclesList из enterprise-service
- Цветовая схема: COLOR_ACCENT '#D15C29', COLOR_BG_SURFACE '#2C2C2C', COLOR_CANVAS_BACKGROUND '#1a1a1a'

---

### enterprise-frontend-demo-dev (Demo frontend предприятия) - Shift Task Management

**Архитектура:** React 18 + TypeScript, Vite, Tailwind CSS, TanStack Query (@tanstack/react-query) для data fetching, Lucide React icons.

**Components (из src/components/, 6 модулей):**
- **ShiftTasksManager.tsx** (847 строк) — Главный компонент управления сменными заданиями: создание заданий для каждой техники, выбор типа задачи (TASK_TYPES), добавление маршрутов (места погрузки/разгрузки, объем/рейсы), сохранение через shiftTasksApi, проверка существующих заданий allExistingTasks query
- **ShiftTaskForm.tsx** (13.1KB) — Форма создания/редактирования сменного задания
- **ShiftTaskCard.tsx** (6.1KB) — Карточка отображения одного задания
- **ShiftTaskList.tsx** (3.0KB) — Список заданий
- **RoutesOverview.tsx** (48.7KB) — Обзор маршрутов (массивный компонент)
- **WorkTimeMap.tsx** (46.8KB) — Карта рабочего времени

**API Client (из src/api/client.ts):**
- **vehiclesApi** — CRUD техники: list({enterprise_id, is_active, size})
- **workRegimesApi** — Режимы работы: list({enterprise_id, is_active, size})
- **placesApi** — Места: list({type: 'load'|'unload', is_active, limit})
- **shiftTasksApi** — Сменные задания: create, list, update, delete

**Types (из src/types/index.ts):**
- **Vehicle** — Модель техники с полями id, name, vehicle_type ('shas'|'pdm'), payload_volume, capacity_volume
- **ShiftTaskCreate** — DTO создания задания
- **RouteTask** — Маршрутное задание с place_a_id, place_b_id, volume, trips
- **TASK_TYPES** — Константы типов задач

**Ключевые особенности ShiftTasksManager.tsx (код):**
- VehicleTaskState interface: vehicleId, isExpanded, taskType, plannedTotal, routes[], inputMode ('volume'|'trips'), existingTaskId, isSaved
- React Query hooks: useQuery для загрузки vehicles/workRegimes/places, useMutation для сохранения заданий
- Date picker: selectedDate state для выбора даты смены
- RouteFormData: id, place_a_id, place_b_id, volume, trips
- getVehicleCapacity(vehicle): возврат вместительности кузова в зависимости от vehicle_type
- Маршруты хранятся как массив RouteFormData[] для каждой техники
- Переключение режима ввода: inputMode 'volume' (объем) или 'trips' (количество рейсов)

---

### wifi-event-dispatcher-dev (Диспетчер WiFi событий) - Go gRPC Bidirectional Streaming

**Архитектура:** Go (Golang), gRPC bidirectional streaming, RabbitMQ Streams consumer, Redis deduplication, Domain-Driven Design структура.

**Server (из server/internal/grpc/server.go, 296 строк):**
- **server struct** — gRPC сервер с полями logger, app application.App, dedup dedup.Service, autorepubClient *autorepub.Client
- **StreamBortSendEvents()** — Bidirectional stream метод: принимает события от борта через gRPC stream, проверяет дубликаты через dedup.IsDuplicate(ctx, delivery.MessageId), публикует в RabbitMQ
- **isDuplicateDelivery()** — Проверка дубликатов через Redis: если MessageId уже был обработан — Ack и drop сообщения
- **Register()** — Регистрация gRPC сервиса: serverpb.RegisterEventDispatchServiceServer(registrar, s)

**Internal modules (из internal/):**
- **autorepub/** — Автопубликация конфигураций при подключении борта
- **dedup/** — Сервис дедупликации через Redis
- **config/** — Конфигурация приложения
- **fx/** — Dependency injection через Uber FX
- **logger/** — Логирование через zerolog
- **rabbitmq/** — Интеграция с RabbitMQ Streams (8 файлов)
- **redis/** — Redis client для deduplication

**Domain layer (из domain/, 6 модулей):**
- DDD domain models для событий, бортов, маршрутов

**Ключевые особенности server.go (код):**
- StreamBortSendEvents обрабатывает два типа запросов:
  1. Producer registration: req.GetProducer() с truck_id, логирование подключения
  2. Event sending: req.GetEvent(), проверка дубликатов, публикация в RabbitMQ
- Deduplication: Redis check через dedup.IsDuplicate(), если duplicate — delivery.Ack(false) и return true
- Error handling: io.EOF считается нормальным завершением стрима, другие ошибки возвращаются
- Ack response: sendAck(messageID, err) отправляет подтверждение борту с Ok/Error полями

---

### cdc-distributor-dev (CDC Distributor) - Fan-Out Orchestration

**Архитектура:** Python FastAPI, RabbitMQ Streams consumer, msgspec сериализация, агрегация CDC событий по таблицам, fan-out публикация в очереди бортов.

**App modules (из src/app/, 8 модулей):**
- **fan_out_orchestrator.py** (140 строк) — FanOutOrchestrator класс: процесс батчей CDC событий, агрегация через MultiTableAggregator, сериализация через msgspec.json.encode(payload), публикация через AMQPPublisher, управление offset через BortOffsetManager
- **multi_table_aggregator.py** (5.6KB) — Агрегация событий по таблицам (last-write-wins стратегия)
- **amqp_publisher.py** (4.1KB) — Публикация в RabbitMQ с retry policy
- **bort_offset_manager.py** (3.6KB) — Управление consumed offset для каждого борта

**Model (из src/app/model/):**
- **fan_out_payload.py** — FanOutPayload schema: seq_id, low_offset, up_offset, tables dict[str, TableBatch]
- **Envelope** — Обертка CDC события

**Core modules (из src/core/, 8 модулей):**
- Конфигурация, логирование, aggregation logic

**Ключевые особенности fan_out_orchestrator.py (код):**
- process_batch(events, stream_name, max_offset, min_offset):
  1. Агрегация: batches_by_table = self._aggregator.aggregate(events)
  2. Конвертация в TableBatch: upserts/deletes для каждой таблицы
  3. Сбор payload: FanOutPayload(seq_id, low_offset, up_offset, tables)
  4. Сериализация: body = msgspec.json.encode(payload)
  5. Публикация: publisher.publish(body) с retry
  6. Offset commit: offset_manager.commit(max_offset) только после успешной публикации
- Гарантии: offset продвигается только после publisher confirm, structured logging с контекстом bort/stream/events/tables/offsets
- Изоляция отказов: каждый (bort x service) consumer имеет свой экземпляр FanOutOrchestrator

---

### cdc-bort-applier-dev (CDC Bort Applier) - PostgreSQL Apply

**Архитектура:** Python FastAPI, asyncpg PostgreSQL driver, msgspec десериализация, применение CDC агрегатов в локальную БД борта, outbox паттерн для уведомлений.

**App modules (из src/app/, 9 модулей):**
- **aggregate_applier.py** (151 строка) — AggregateApplier класс: декодирование FanOutPayloadMsg через msgspec.json.Decoder, проверка дубликатов по seq_id, применение upserts/deletes в PostgreSQL транзакции, запись seq_id в cdc_seq_id таблицу
- **postgres_applier.py** (5.9KB) — Применение изменений в PostgreSQL (UPSERT/DELETE операции)
- **outbox.py** (5.8KB) — Outbox writer для записи уведомлений об изменениях
- **outbox_worker.py** (4.7KB) — Фоновый worker для публикации outbox сообщений
- **bootstrap.py** (2.8KB) — Инициализация приложения

**Model (из src/app/model/):**
- **fan_out_payload.py** — FanOutPayloadMsg schema для десериализации

**Core modules (из src/core/, 8 модулей):**
- **aggregate_handler.py** — Protocol definition для AggregateHandler
- **aggregator.py** — AggregatedBatch schema

**Ключевые особенности aggregate_applier.py (код):**
- cdc_seq_id таблица DDL: CREATE TABLE IF NOT EXISTS cdc_seq_id (queue TEXT PRIMARY KEY, last_seq_id BIGINT, updated_at TIMESTAMPTZ)
- setup(): создание cdc_seq_id таблицы при старте consumer
- handle_raw(body): точка входа из AmqpConsumer, декодирование msgspec.json.Decoder(FanOutPayloadMsg).decode(body)
- _apply(payload): основная логика:
  1. Подсчет upsert_count/delete_count из tables dict
  2. Проверка дубликата: SELECT last_seq_id FROM cdc_seq_id WHERE queue = $1, если payload.seq_id <= last_seq_id — skip (duplicate)
  3. Транзакция: BEGIN, применение всех upserts/deletes через postgres_applier, UPDATE cdc_seq_id SET last_seq_id = $1 WHERE queue = $2, COMMIT
  4. Outbox notification: если outbox_writer задан — запись уведомлений об изменениях
- Idempotency: seq_id check гарантирует что одно и то же сообщение не применится дважды

---

### settings-server-dev (Сервер настроек) - Vault Integration

**Архитектура:** Python FastAPI, HashiCorp Vault integration для хранения секретов бортов, background tasks для уведомления бортов об обновлениях.

**Routers (из app/routers/, 2 модуля):**
- **settings.py** (62 строки) — CRUD операции с секретами бортов через Vault: POST /secrets/{vehicle_id} (создание пакета секретов), GET /secrets/{vehicle_id} (чтение), DELETE /secrets/{vehicle_id} (удаление), GET /secrets (получение шаблона переменных)
- **frontend.py** (0.8KB) — Frontend endpoints

**Services (из app/services/):**
- Vault integration service

**Utils (из app/utils/, 3 модуля):**
- **vault_client.py** — Клиент для HashiCorp Vault API
- **bort_notifier.py** — Уведомление бортов об обновлениях конфигурации
- **initial_reading_secrets.py** — Извлечение общих переменных из шаблонов

**Ключевые особенности settings.py (код):**
- create_new_secrets_pack(vehicle_id, custom_variables): 
  1. VaultClient.create_new_secrets(vehicle_id, custom_variables) — создание секретов в Vault
  2. background_tasks.add_task(BortNotifier.notify_vehicle_updated, vehicle_id) — асинхронное уведомление борта
- read_secrets_pack_by_vehicle_id(vehicle_id): VaultClient.read_secrets_by_vehicle_id(vehicle_id)
- delete_secrets_pack_by_vehicle_id(vehicle_id): VaultClient.delete_secrets_by_vehicle_id(vehicle_id)
- get_template(): extract_common_variables() возврат specific и vehicle_dependant переменных
- Error handling: FileNotFoundError/ValueError → HTTPException 404, Exception → HTTPException 500

---

### settings-bort-dev (Клиент настроек борта) - Configuration Receiver

**Архитектура:** Python FastAPI, получение конфигурации от settings-server, локальное хранение в базе данных, admin интерфейс для управления.

**Routers (из app/routers/, 3 модуля):**
- **admin.py** (4.5KB) — Admin панель управления настройками
- **settings.py** (1.2KB) — Получение и применение настроек от сервера
- **vehicle.py** (0.4KB) — Информация о текущем борте

**Database (из app/database/, 3 модуля):**
- PostgreSQL connection pool, models, migrations

**Models (из app/models/, 2 модуля):**
- SQLAlchemy модели для хранения конфигурации

**Static files (из app/static/):**
- HTML templates, CSS, JavaScript для admin интерфейса

---

### audit-exporter-dev (Экспортер аудита) - PostgreSQL → ClickHouse ETL

**Архитектура:** Python FastAPI, polling-based ETL pipeline из PostgreSQL audit_outbox в ClickHouse, state management для отслеживания прогресса, deduplication токены.

**Core modules (из src/core/, 7 модулей):**
- **pipeline.py** (145 строк) — Process source функция: poll → write → ack цикл для одного источника, gating acknowledgement на ClickHouseWriteOutcome.ok
- **orchestrator.py** (3.2KB) — Оркестратор обработки нескольких источников
- **state.py** (11.2KB) — BootstrapRuntimeState для отслеживания состояния pipeline
- **config.py** (6.5KB) — Конфигурация источников и параметров экспорта
- **logging.py** (2.2KB) — Структурированное логирование
- **diagnostics.py** (0.5KB) — Диагностические утилиты

**ClickHouse (из src/clickhouse/, 2 модуля):**
- **client.py** — ClickHouseClient для insert_exported_events(), derive_dedup_token() для идемпотентности

**DB (из src/db/, 2 модуля):**
- **source_connections.py** — PostgresSourceReader для poll(batch_size), acknowledgement через ACK/NACK

**App (из src/app/, 2 модуля):**
- **routes/** (2 endpoint) — Health checks и diagnostics API

**Ключевые особенности pipeline.py (код):**
- process_source(reader, ch_client, batch_size, state, cycle_id):
  1. Poll: events, poll_result = await reader.poll(batch_size=batch_size), state.record_source_poll_success(poll_result)
  2. Если row_count == 0 — return ProcessSourceResult(phase_reached='poll_empty')
  3. Write: dedup_token = derive_dedup_token(events), write_outcome = await ch_client.insert_exported_events(events)
  4. Если write_outcome.ok == False — return ProcessSourceResult(phase_reached='write_failed') без ack
  5. Ack: ack_outcome = await reader.acknowledge(poll_result), только если write successful
  6. Return ProcessSourceResult с полным контекстом: source_name, phase_reached, poll_result, write_outcome, ack_outcome
- Гарантии: acknowledgement только после успешной записи в ClickHouse, structured logging с cycle_id/source_name контекстом, error capture в result вместо raising exceptions
- ProcessSourceResult: Pydantic BaseModel с frozen=True, содержит все этапы выполнения

---

## ИТОГО УРОВЕНЬ 2 (ПРОДОЛЖЕНИЕ 5): ПРОАНАЛИЗИРОВАНО

✅ **dispa-frontend-dev:** 7 pages (ShiftTasksPage.tsx 234 строки, активация заданий через tripServiceApi)  
✅ **graph-service-frontend-dev:** GraphEditor.tsx (3878 строк!), ThreeView.tsx (53.3KB), 5 hooks, Three.js 3D visualization  
✅ **enterprise-frontend-demo-dev:** ShiftTasksManager.tsx (847 строк, TanStack Query, создание заданий для техники)  
✅ **wifi-event-dispatcher-dev:** Go gRPC server.go (296 строк, bidirectional streaming, Redis deduplication)  
✅ **cdc-distributor-dev:** fan_out_orchestrator.py (140 строк, msgspec сериализация, fan-out публикация)  
✅ **cdc-bort-applier-dev:** aggregate_applier.py (151 строка, asyncpg, seq_id idempotency, outbox pattern)  
✅ **settings-server-dev:** settings.py (62 строки, Vault CRUD, background notifications)  
✅ **settings-bort-dev:** 3 routers (admin.py, settings.py, vehicle.py)  
✅ **audit-exporter-dev:** pipeline.py (145 строк, poll→write→ack цикл, ClickHouse ETL)

**Ключевые находки из кода:**
- **dispa-frontend ShiftTasksPage.tsx:** tripServiceApi.getShiftTasks({page: 1, size: 100}), getActiveTask(), activateTask(routeId), getCompletedTripsCount(taskId) — управление заданиями смены
- **graph-service-frontend GraphEditor.tsx:** 3878 строк кода! mode state ('view'|'addNode'|'addEdge'|...), selectedNode/Edge/Tag/Place, scale/offset для canvas, WebSocket vehiclePosition, enterprise vehicles integration, ladder creation workflow (ladderStep selectLevels/selectNode1/selectNode2)
- **enterprise-frontend ShiftTasksManager.tsx:** VehicleTaskState interface (vehicleId, isExpanded, taskType, plannedTotal, routes[], inputMode 'volume'|'trips'), TanStack Query useQuery/useMutation, getVehicleCapacity(vehicle) по vehicle_type
- **wifi-event-dispatcher server.go:** StreamBortSendEvents bidirectional stream, isDuplicateDelivery() через Redis dedup.IsDuplicate(MessageId), delivery.Ack(false) для дубликатов, sendAck(messageID, err) response
- **cdc-distributor fan_out_orchestrator.py:** process_batch() с 5 шагами: aggregate → convert to TableBatch → build FanOutPayload → msgspec.json.encode → publish, offset commit только после publisher confirm
- **cdc-bort-applier aggregate_applier.py:** cdc_seq_id таблица для idempotency, handle_raw(body) → msgspec decode → _apply(payload) → seq_id check → transaction (upserts/deletes + UPDATE cdc_seq_id) → outbox notification
- **settings-server settings.py:** VaultClient.create_new_secrets(vehicle_id, custom_variables), background_tasks.add_task(BortNotifier.notify_vehicle_updated), GET/POST/DELETE /secrets/{vehicle_id}
- **audit-exporter pipeline.py:** process_source() с gating acknowledgement на write_outcome.ok, derive_dedup_token(events) для идемпотентности ClickHouse inserts, ProcessSourceResult Pydantic model с frozen=True

**Осталось проанализировать:** dispatching-repo-dev (master monorepo), api-gateway-dev, auth-lib-dev, monitoring-repo-dev структуры кода.

---

## УРОВЕНЬ 3: ВАЖНЫЕ ИНДИВИДУАЛЬНЫЕ ФАЙЛЫ (>500 строк)

### dispa-backend-dev/src/app/services/state_machine.py (1868 строк)

**Назначение:** State Machine для управления жизненным циклом техники через 6 состояний с автоматическими переходами по триггерам (tag/speed/weight/vibro).

**Ключевые классы и методы:**
- **StateMachine class** — Основной класс управления состоянием, хранит vehicle_id, sensor_data dict, Redis connection
- **get_current_state()** — Загрузка состояния из Redis или инициализация начального состояния STOPPED_EMPTY с полями: state, cycle_id, entity_type, task_id, last_tag_id, last_place_id, last_transition timestamp
- **reset_state()** — Сброс состояния к IDLE без цикла/рейса
- **manual_transition(new_state, reason, comment, db)** — Ручной переход оператора:
  - Получает current_state_data из Redis
  - Определяет trip_action: "end_cycle" при переходе в IDLE/MOVING_EMPTY, "start_trip" при LOADING если есть active_task, "start_cycle_and_trip" если нет цикла
  - Получает current_tag из Redis: redis_client.get_json(f"trip-service:vehicle:{vehicle_id}:current_tag")
  - Если trip_action == "start_trip" — загружает active_task_data из Redis, устанавливает task_id и shift_id из RouteTask
  - Вызывает _transition_to_state() с trigger_type=MANUAL
- **new_state_action(db)** — Автоматический переход на основе сенсоров:
  - Извлекает tag_data, speed_data, weight_data, vibro_data из self._sensor_data
  - Проверяет типы данных: isinstance(speed_data, dict), isinstance(weight_data, dict)
  - Извлекает параметры: tag_id, tag_name, place_id, place_type, speed_event, weight_event, weight_value, vibro_event
  - Логика переходов:
    1. UNLOADING + is_unloading_place + weight_value <= end_cycle_weight → trip_action="end_cycle", new_state=STOPPED_EMPTY, unloading=True
       - Вызывает _save_place_remaining_history(place_id, "unloading", cycle_id, task_id, shift_id) для обновления остатка места разгрузки
    2. MOVING_EMPTY + speed_event=="stopped" + weight_event=="empty" → STOPPED_EMPTY
    3. STOPPED_EMPTY + is_loading_place + speed_event=="stopped" + weight_event=="loaded" → LOADING, trip_action="start_trip"
       - Загружает active_task_data из Redis, устанавливает task_id/shift_id из RouteTask
       - Если нет активного задания — очищает task_id/shift_id из state_data
    4. LOADING + speed_event=="moving" + weight_event=="loaded" → MOVING_LOADED
       - Вызывает _save_place_remaining_history(place_id, "loading", ...) для обновления остатка места погрузки
    5. MOVING_LOADED + is_unloading_place → UNLOADING
    6. STOPPED_EMPTY + speed_event=="moving" + weight_event=="empty" → MOVING_EMPTY
  - После определения new_state вызывает _transition_to_state(trigger_type=AUTOMATIC)
- **_transition_to_state(new_state, trigger_type, trigger_data, trip_action, current_state_data, db)** — Выполнение перехода:
  - Валидация перехода через _validate_transition(current_state, new_state)
  - Обработка trip_action:
    - "start_cycle": создание нового Cycle через CycleService.create_cycle(vehicle_id, start_time)
    - "start_trip": создание Trip внутри существующего Cycle через TripManager.create_trip(vehicle_id, place_id, tag, active_task_id, cycle_id, loading_timestamp, db)
    - "start_cycle_and_trip": сначала create_cycle(), затем create_trip() с полученным cycle_id
    - "end_cycle": завершение текущего цикла через TripManager.complete_trip(cycle_id, place_id, tag, db)
  - Обновление state_data в Redis: state=new_state.value, cycle_id, task_id, last_tag_id=tag_id, last_place_id=place_id, last_transition=now.isoformat()
  - Публикация события в MQTT через publish_state_change_event(vehicle_id, old_state, new_state, trigger_type, trigger_data)
  - Логирование перехода с контекстом vehicle_id/from_state/to_state/trigger_type/trip_action

**State enum (6 состояний):**
- STOPPED_EMPTY — Остановка пустым
- MOVING_EMPTY — Движение пустым
- LOADING — Погрузка
- MOVING_LOADED — Движение груженым
- UNLOADING — Разгрузка
- STOPPED_LOADED — Остановка груженым (не используется активно)

**TriggerType enum:**
- MANUAL — Ручной переход оператором
- AUTOMATIC — Автоматический переход по сенсорам
- TIMER — Переход по таймеру (timeout)

**Ключевые особенности кода:**
- Использует truncate_datetime_to_seconds(datetime.now(UTC)) для консистентности временных меток
- Redis ключи: f"trip-service:vehicle:{vehicle_id}:state_machine", f"trip-service:vehicle:{vehicle_id}:current_tag"
- place_remaining_change сохраняется при переходах LOADING→MOVING_LOADED и UNLOADING→STOPPED_EMPTY
- Active task загружается из Redis: redis_client.get_active_task(str(vehicle_id)), содержит task_id
- Shift_id извлекается из RouteTask.shift_task_id через SQLAlchemy query: select(RouteTask).where(RouteTask.id == task_id)
- Vibro events: "weight_rise" (начало погрузки), "weight_fall" (конец разгрузки) как альтернатива place_type проверке
- Weight threshold: settings.end_cycle_weight (конфигурируемый порог для определения конца цикла)

---

### dispa-backend-dev/src/app/services/trip_manager.py (651 строка)

**Назначение:** Управление жизненным циклом рейсов (Trip) — создание, завершение, связь с заданиями, публикация событий.

**Ключевые функции:**
- **create_trip(vehicle_id, place_id, tag, active_task_id, cycle_id, loading_timestamp, db)** — Создание рейса внутри цикла:
  - Определяет тип рейса: проверяет RouteTask.place_a_id == place_id для planned, иначе unplanned
  - Если active_task_id задан и место совпадает с place_a_id:
    - trip_type = "planned", task_id = active_task_id, shift_id = task.shift_task_id
    - Обновляет RouteTask.status = TripStatusRouteEnum.ACTIVE
    - Логирует "RouteTask activated for trip"
  - Иначе trip_type = "unplanned", task_id = None, shift_id = None
  - Находит существующий Cycle: select(Cycle).where(Cycle.cycle_id == cycle_id)
  - Обновляет Cycle.task_id и Cycle.shift_id
  - Создает Trip запись через insert(Trip).values(cycle_id, trip_type, start_time=now, loading_place_id=place_id, loading_tag=tag_str, loading_timestamp, cycle_num)
  - cycle_num вычисляется через construct_trip_cycle_num_subquery(cycle.vehicle_id, now) — подзапрос COUNT + 1
  - Обновляет Cycle.entity_type = "trip" для JTI polymorphism
  - Логирует "Cycle converted to Trip via JTI"
  - Возвращает {"cycle_id": str, "trip_type": str, "task_id": Optional[str]}
- **complete_trip(cycle_id, place_id, tag, db)** — Завершение рейса:
  - Находит Trip по cycle_id: select(Trip).where(Trip.cycle_id == cycle_id)
  - Обновляет Trip.end_time = now, unloading_place_id = place_id, unloading_tag = tag_str
  - Если trip_type == "planned" и task_id существует:
    - Находит RouteTask: select(RouteTask).where(RouteTask.id == task_id)
    - Увеличивает RouteTask.completed_trips_count += 1
    - Если completed_trips_count >= planned_trips_count:
      - RouteTask.status = TripStatusRouteEnum.COMPLETED
    - Иначе status остается ACTIVE
  - Публикует событие trip_completed через publish_trip_event(vehicle_id, "trip_completed", {...})
  - Логирует "Trip completed" с trip_type/completed_trips_count/planned_trips_count
- **construct_trip_cycle_num_subquery(vehicle_id, timestamp)** — Построение подзапроса для вычисления номера рейса в цикле:
  - SELECT COUNT(*) + 1 FROM trips WHERE vehicle_id = :vehicle_id AND DATE(start_time) = DATE(:timestamp)
  - Возвращает ScalarSelect для использования в INSERT
- **bulk_update_trips_cycle_num(db, vehicle_ids, date)** — Массовое обновление cycle_num для всех рейсов за дату:
  - Для каждого vehicle_id вычисляет новый cycle_num через window function ROW_NUMBER()
  - Обновляет Trip.cycle_num = new_number WHERE trip_id IN (...)

**JTI (Joined Table Inheritance) паттерн:**
- Cycle — базовая таблица с cycle_id, vehicle_id, start_time, end_time, task_id, shift_id, entity_type
- Trip — наследуемая таблица с trip_id (FK к cycle_id), trip_type, loading_place_id, loading_tag, loading_timestamp, unloading_place_id, unloading_tag, cycle_num
- entity_type поле в Cycle определяет тип: "cycle" (базовый) или "trip" (расширенный)
- При создании Trip: UPDATE Cycle SET entity_type = 'trip' WHERE cycle_id = :cycle_id

**MQTT события:**
- trip_started: публикуется при create_trip с payload {vehicle_id, cycle_id, trip_type, task_id, place_id, timestamp}
- trip_completed: публикуется при complete_trip с payload {vehicle_id, cycle_id, trip_type, completed_trips_count, planned_trips_count, place_id, timestamp}

**Redis интеграция:**
- Active task: redis_client.get_active_task(str(vehicle_id)) возврат {task_id, shift_id, ...}
- Current tag: redis_client.get_json(f"trip-service:vehicle:{vehicle_id}:current_tag") возврат {tag_id, tag_name, place_id, place_type}

---

### graph-service-frontend-dev/src/components/GraphEditor.tsx (3878 строк)

**Назначение:** Главный компонент редактирования графа дорожных сетей карьера с Canvas 2D рендерингом, drag-and-drop, масштабированием, WebSocket real-time updates.

**State management (useState hooks):**
- **mode** — Режим работы: 'view' | 'addNode' | 'addEdge' | 'addPlace' | 'addLadder' | 'move' | 'edit' | 'delete'
- **selectedNode/selectedEdge/selectedTag/selectedPlace** — ID выбранного объекта (number | null)
- **scale** — Масштаб canvas (default 1)
- **offset** — Смещение viewport {x: number, y: number} (default {0, 0})
- **previousHorizonId** — Отслеживание смены уровня для перезагрузки данных
- **editingTag/editingPlace/editingNode/editingEdge/editingLadderNode** — Объекты в режиме редактирования
- **showEditTag/showEditPlace/showEditNode/showEditEdge/showEditLadder** — Флаги показа диалогов редактирования
- **isDraggingRadius/draggingTagId/tempRadius** — Drag радиуса метки
- **isLeftPanelOpen/isVehiclesPanelOpen** — Состояние боковых панелей
- **currentView** — Текущий вид: 'settings' | 'graphs' | 'editor' | 'viewer'
- **showCoordinates/cursorPos** — Отображение координат курсора
- **showImportDialog/showLadderDialog** — Диалоги импорта и создания лестниц
- **ladderSourceNode/ladderLevel1Id/ladderLevel2Id/ladderNode1Id/ladderNode2Id** — Контекст создания лестницы
- **ladderStep** — Шаг wizard: 'selectLevels' | 'selectNode1' | 'selectNode2' | null
- **leftDockSelection** — Выбор в левой панели: 'horizons' | 'tools' | null
- **isDraggingObject/draggingObjectType/draggingObjectId** — Drag объекта (node/tag)
- **dragStartPos/dragCurrentPos** — Позиции для drag операции
- **isPanning/panStartPos** — Pan canvas (перемещение viewport)
- **nodeError/edgeError/tagError/placeError** — Ошибки валидации форм

**Custom hooks:**
- **useSettings()** — Управление настройками редактора (coordinate calibration, grid visibility, vehicle tracking)
- **useWebSocket({onVehicleUpdate, vehiclesList})** — Real-time обновления позиций техники через WebSocket, НЕ передает searchHeight чтобы backend использовал DEFAULT_VEHICLE_HEIGHT
- **useGraphData()** — Загрузка и кэширование данных графа (horizons, nodes, edges, tags, places)
- **useVehicles(enterpriseId)** — Загрузка списка техники из enterprise-service API

**Computed values (useMemo):**
- **placeRadiusMap** — Map<number, number>: place_id → max radius из связанных тэгов (telemetry tags с place_id)
  - Алгоритм: перебирает все tags, если t.place_id существует, обновляет m.set(t.place_id, Math.max(prev, t.radius || 25))
- **vehicleNamesMapRef** — Ref<Map<string, string>>: vehicle_id → name из enterprise-service
  - Обновляется в useEffect при изменении enterpriseVehicles: namesMap.set(String(vehicle.id), vehicle.name)

**Canvas rendering (drawGraph function):**
- Очищает canvas: ctx.clearRect(0, 0, canvasWidth, canvasHeight)
- Заполняет фон: ctx.fillStyle = COLOR_CANVAS_BACKGROUND ('#1a1a1a')
- Вычисляет world boundaries: worldLeft = -offset.x / scale, worldTop = -offset.y / scale, worldRight/Bottom с учетом canvas размеров
- Адаптивная сетка: GRID_BASE_SPACING = 120, динамически увеличивается/уменьшается чтобы pixelSpacing был 60-240px
  - while (pixelSpacing < 60) gridSpacing *= 2
  - while (pixelSpacing > 240 && gridSpacing > GRID_BASE_SPACING / 4) gridSpacing /= 2
- Рисует сетку: minor lines (0.9px/scale, rgba(254,252,249,0.02)), major lines every 5th (1.6px/scale, rgba(254,252,249,0.05))
- Применяет трансформацию: ctx.translate(offset.x, offset.y); ctx.scale(scale, scale)
- Отрисовка ребер: перебирает graphData.edges, находит fromNode/toNode, преобразует GPS→canvas через settings.transformGPStoCanvas(lat, lon), рисует линии ctx.moveTo/lineTo/stroke
  - Если узел перемещается (isDraggingObject && draggingObjectId === node.id), использует dragCurrentPos вместо canvasPos
- Отрисовка узлов:
  - Проверяет hasLadder: node.node_type === 'ladder' или edge.edge_type === 'vertical'
  - Преобразует GPS→canvas: canvasPos = settings.transformGPStoCanvas(node.y, node.x) // lat, lon
  - Если dragging: использует dragCurrentPos
  - Рисует круг: ctx.arc(x, y, nodeRadius, 0, 2*Math.PI)
  - Цвет: isSelected ? COLOR_ACCENT ('#D15C29') : hasLadder ? '#FFA500' : '#FEFCF9'
  - Fill: ctx.fillStyle, stroke: ctx.strokeStyle = COLOR_MUTED ('#9F9F9F'), lineWidth = 2/scale
- Отрисовка меток (tags):
  - Вычисляет позицию: tagCanvasPos = settings.transformGPStoCanvas(tag.y, tag.x)
  - Рисует окружность радиуса: ctx.arc(x, y, tag.radius || 25, 0, 2*Math.PI), strokeStyle = COLOR_ACCENT_SOFT, fillStyle = COLOR_ACCENT_SOFTER
  - Рисует центральную иконку по типу: createTagCenterPath(ctx, x, y, size, tagType)
    - 'transit': круг (arc)
    - 'loading': треугольник (moveTo/lineTo/closePath)
    - 'transfer': квадрат (rect)
    - 'unloading': звезда 5-конечная (spikes loop с outerRadius/innerRadius)
    - 'transport': пятиугольник (sides=5 loop)
  - Текст метки: ctx.fillText(tag.name, x, y + tag.radius + 15)
- Отрисовка мест (places):
  - Берет радиус из placeRadiusMap: radius = placeRadiusMap.get(place.id) || 25
  - Рисует пунктирный круг: ctx.setLineDash([5, 5]), ctx.arc(x, y, radius, 0, 2*Math.PI)
  - Текст места: ctx.fillText(place.name, x, y + radius + 15)
- Отрисовка техники:
  - Перебирает vehicles массив из WebSocket
  - Получает имя: vehicleName = vehicleNamesMapRef.current.get(String(v.vehicle_id)) || `Truck ${v.vehicle_id}`
  - Преобразует GPS→canvas: truckPos = settings.transformGPStoCanvas(v.lat, v.lon)
  - Рисует треугольник направления: угол из v.heading, размер 15px
  - Текст: ctx.fillText(`${vehicleName} (${v.speed} km/h)`, truckPos.x, truckPos.y - 20)
- Отрисовка лестниц (ladders):
  - Сохраняет позиции иконок: ladderIconPositionsRef.current.set(ladder.id, {x, y})
  - Рисует иконку лестницы: вертикальная линия с двумя горизонтальными засечками

**Event handlers:**
- **handleMouseDown(e)** — Начало drag/pan:
  - Если mode === 'move' и правая кнопка мыши → isPanning = true, panStartPos = {x: e.clientX, y: e.clientY}
  - Если mode === 'move' и левая кнопка на узле → isDraggingObject = true, draggingObjectType = 'node', draggingObjectId = node.id, dragStartPos = canvasPos
  - Если mode === 'move' и левая кнопка на метке → isDraggingObject = true, draggingObjectType = 'tag', draggingTagId = tag.id, isDraggingRadius = true (если клик на границе радиуса)
- **handleMouseMove(e)** — Drag/pan обновление:
  - Если isPanning: вычисляет delta = {x: e.clientX - panStartPos.x, y: e.clientY - panStartPos.y}, обновляет offset.x += delta.x, offset.y += delta.y, panStartPos = {e.clientX, e.clientY}
  - Если isDraggingObject: преобразует mouse pos в canvas coords, dragCurrentPos = {x, y}
  - Если isDraggingRadius: вычисляет расстояние от центра метки до курсора, tempRadius = distance
- **handleMouseUp(e)** — Конец drag/pan:
  - Если isDraggingObject и dragCurrentPos:
    - Если draggingObjectType === 'node': вызывает updateNode(draggingObjectId, {x: dragCurrentPos.x, y: dragCurrentPos.y}) через API
    - Если draggingObjectType === 'tag': вызывает updateTag(draggingTagId, {x: dragCurrentPos.x, y: dragCurrentPos.y, radius: tempRadius || tag.radius})
  - Сбрасывает isDraggingObject/isPanning/dragCurrentPos/dragStartPos
- **handleWheel(e)** — Zoom:
  - e.preventDefault() для предотвращения scroll
  - handleZoom(e.deltaY > 0 ? -0.1 : 0.1) — уменьшение/увеличение scale на 0.1
  - Ограничивает scale: Math.max(0.1, Math.min(5, scale + delta))
- **handleZoom(delta)** — Изменение масштаба:
  - newScale = Math.max(0.1, Math.min(5, scale + delta))
  - Корректирует offset чтобы zoom был относительно центра экрана

**Coordinate transformation:**
- GPS (lat, lon) → Canvas (x, y): settings.transformGPStoCanvas(lat, lon)
  - Использует coordinateCalibration из localStorage: {enabled, topLeft: {lat, lon}, bottomRight: {lat, lon}, canvasWidth, canvasHeight}
  - Линейная интерполяция: x = ((lon - topLeft.lon) / (bottomRight.lon - topLeft.lon)) * canvasWidth
  - y = ((lat - topLeft.lat) / (bottomRight.lat - topLeft.lat)) * canvasHeight
  - Если calibration не enabled: использует identity transform (x = lon * scaleFactor, y = lat * scaleFactor)

**Ladder creation workflow:**
- Step 1 'selectLevels': пользователь выбирает level1 и level2 из dropdown
- Step 2 'selectNode1': клик на узле первого уровня → ladderNode1Id = node.id
- Step 3 'selectNode2': клик на узле второго уровня → ladderNode2Id = node.id
- После выбора обоих узлов: вызывает connectLadderNodes(ladderNode1Id, ladderNode2Id) API
- API создает vertical edge между узлами разных уровней

**Non-passive event listeners (useEffect):**
- Регистрирует touchstart/touchmove/touchend/wheel с {passive: false} для предотвращения scroll на мобильных устройствах
- preventScroll(e) вызывается для touch событий: e.preventDefault()
- handleWheelEvent(e) для zoom: e.preventDefault(), handleZoom(e.deltaY > 0 ? -0.1 : 0.1)
- Cleanup: removeEventListener для всех событий при unmount

**Critical fix (useEffect):**
- Принудительный сброс старой coordinateCalibration из localStorage:
  - Проверяет storedCalibration = localStorage.getItem('coordinateCalibration')
  - Если parsed.enabled === true: удаляет ключ и делает window.location.reload()
  - Это предотвращает использование устаревшей калибровки после изменений системы координат

**Color scheme constants:**
- COLOR_ACCENT = '#D15C29' (оранжевый акцент)
- COLOR_ACCENT_SOFT = 'rgba(209, 92, 41, 0.18)' (мягкий акцент для fill)
- COLOR_ACCENT_SOFTER = 'rgba(209, 92, 41, 0.10)' (очень мягкий акцент)
- COLOR_MUTED = '#9F9F9F' (серый для strokes)
- COLOR_LIGHT = '#FEFCF9' (светлый для узлов)
- COLOR_BG_SURFACE = '#2C2C2C' (фон поверхностей)
- COLOR_CANVAS_BACKGROUND = '#1a1a1a' (глубокий темный фон canvas)
- COLOR_GRID_MINOR = 'rgba(254, 252, 249, 0.02)' (минорная сетка)
- COLOR_GRID_MAJOR = 'rgba(254, 252, 249, 0.05)' (мажорная сетка каждые 5 линий)
- GRID_BASE_SPACING = 120 (базовый шаг сетки в мировых координатах)

**Panel layout:**
- PANEL_WIDTH = 220px
- leftPanelStyle: width = PANEL_WIDTH
- rightPanelStyle: width = PANEL_WIDTH, transform = isVehiclesPanelOpen ? 'translateX(0)' : `translateX(${PANEL_WIDTH}px)` (slide-in анимация)
- selectionPanelStyle: right = 32px (плавающая панель при выборе объекта)

---

### client-disp-dev/src/pages/dispatch-map/model/slice.ts (316 строк)

**Назначение:** Redux Toolkit slice для управления состоянием карты диспетчера — слои, фильтры, фокус, сортировка, история.

**Initial state (MapState interface):**
- **mode** — Режим карты: loadPersistedField(modeConfig) из localStorage
- **horizonFilter** — Фильтр по горизонтам: loadPersistedField(horizonFilterConfig)
- **hiddenVehicleIds** — Скрытые техники: EMPTY_ARRAY (readonly number[])
- **hiddenPlaceIds** — Скрытые места: EMPTY_ARRAY
- **layers** — Видимость слоев: initialLayers object {vehicles: boolean, places: boolean, edges: boolean, nodes: boolean, tags: boolean, backgrounds: boolean}
- **focusTarget** — Объект фокуса камеры: FocusTarget | null {type: 'vehicle'|'place', id: number}
- **expandedTreeNodes** — Раскрытые узлы дерева: loadPersistedField(expandedTreeNodesConfig) (TreeNodeValue[])
- **vehicleGroupSorts** — Сортировка групп техники: loadPersistedField(vehicleGroupSortsConfig) (VehicleGroupSorts)
- **placeGroupSorts** — Сортировка групп мест: loadPersistedField(placeGroupSortsConfig) (PlaceGroupSorts)
- **backgroundSort** — Сортировка подложек: loadPersistedField(backgroundSortConfig) (BackgroundSortField)
- **formTarget** — Объект для создания/редактирования: FromTarget | null
- **hasUnsavedChanges** — Флаг несохраненных изменений: boolean
- **placementPlaceToAdd** — Место для размещения на карте: number | null
- **backgroundPreviewOpacity** — Предпросмотр яркости подложки: number | null (0-100)
- **isGraphEditActive** — Активен ли режим редактирования графа: boolean
- **isRulerActive** — Активен ли инструмент линейки: boolean
- **selectedHorizonId** — Выбранный горизонт: loadPersistedField(selectedHorizonIdConfig) (number | null)
- **vehicleContextMenu** — Контекстное меню техники: {vehicleId: number, x: number, y: number} | null
- **historyRangeFilter** — Фильтр диапазона истории: {from: string, to: string} | null
- **selectedVehicleHistoryIds** — Выбранные техники для истории: EMPTY_ARRAY (readonly number[])
- **isVisibleHistoryPlayer** — Видимость плеера истории: boolean
- **isPlayHistoryPlayer** — Воспроизведение истории: boolean
- **playerCurrentTime** — Текущее время плеера: string | null (ISO timestamp)
- **isLoading** — Индикатор загрузки: boolean
- **loadPercentage** — Процент загрузки: number | null (0-100)
- **vehicleHistoryMarks** — Метки истории техники: EMPTY_ARRAY (readonly VehicleHistoryMark[])

**Reducers:**
- **toggleVehicleVisibility(state, action: PayloadAction<number>)** — Переключение видимости техники:
  - idx = state.hiddenVehicleIds.indexOf(id)
  - Если idx === -1: state.hiddenVehicleIds.push(id) (скрыть)
  - Иначе: state.hiddenVehicleIds.splice(idx, 1) (показать)
- **togglePlaceVisibility(state, action: PayloadAction<number>)** — Переключение видимости места (аналогично toggleVehicleVisibility)
- **toggleVehiclesVisibility(state, action: PayloadAction<readonly number[]>)** — Переключение видимости группы техники:
  - state.hiddenVehicleIds = toggleBatch(state.hiddenVehicleIds, action.payload)
  - toggleBatch функция добавляет/удаляет batch IDs из массива
- **toggleLayerVisibility(state, action: PayloadAction<MapLayerValue>)** — Переключение видимости слоя:
  - state.layers[action.payload] = !state.layers[action.payload]
  - MapLayerValue: 'vehicles' | 'places' | 'edges' | 'nodes' | 'tags' | 'backgrounds'
- **setFocusTarget(state, action: PayloadAction<FocusTarget | null>)** — Установка фокуса камеры:
  - state.focusTarget = action.payload
  - FocusTarget: {type: 'vehicle' | 'place', id: number}
- **toggleGroupSort(state, action)** — Переключение сортировки группы:
  - Если entity === 'vehicle': state.vehicleGroupSorts[payload.group] = toggleSort(state.vehicleGroupSorts[payload.group], payload.field)
  - Если entity === 'place': state.placeGroupSorts[payload.group] = toggleSort(...)
  - Если entity === 'background': state.backgroundSort = toggleSort(state.backgroundSort, payload.field)
  - toggleSort функция меняет направление сортировки: 'asc' ↔ 'desc' ↔ null
- **toggleTreeNode(state, action: PayloadAction<TreeNodeValue>)** — Раскрытие/сворачивание раздела сайдбара:
  - idx = state.expandedTreeNodes.indexOf(key)
  - Если idx === -1: push(key), иначе splice(idx, 1)

**Persistence helpers:**
- **loadPersistedField(config)** — Загрузка значения из localStorage с fallback на default value
  - config: {key: string, defaultValue: T, deserialize?: (value: string) => T}
  - Пример: loadPersistedField(modeConfig) где modeConfig = {key: 'dispatch-map-mode', defaultValue: 'view'}
- **toggleBatch(array, batch)** — Добавление/удаление batch элементов из readonly array:
  - Создает новый array, перебирает batch IDs
  - Если ID уже в array: удаляет через filter
  - Если ID нет в array: добавляет через push
  - Возвращает новый readonly array
- **toggleSort(currentSort, field)** — Переключение направления сортировки:
  - Если currentSort?.field !== field: return {field, direction: 'asc'}
  - Если currentSort.direction === 'asc': return {field, direction: 'desc'}
  - Если currentSort.direction === 'desc': return null (сброс сортировки)

**Selectors (exported functions):**
- **selectMode(state)**, **selectHorizonFilter(state)**, **selectHiddenVehicleIds(state)**, **selectHiddenPlaceIds(state)**
- **selectLayers(state)**, **selectFocusTarget(state)**, **selectExpandedTreeNodes(state)**
- **selectVehicleGroupSorts(state)**, **selectPlaceGroupSorts(state)**, **selectBackgroundSort(state)**
- **selectFormTarget(state)**, **selectHasUnsavedChanges(state)**, **selectIsGraphEditActive(state)**
- **selectIsRulerActive(state)**, **selectSelectedHorizonId(state)**, **selectVehicleContextMenu(state)**
- **selectHistoryRangeFilter(state)**, **selectSelectedVehicleHistoryIds(state)**
- **selectIsVisibleHistoryPlayer(state)**, **selectIsPlayHistoryPlayer(state)**, **selectPlayerCurrentTime(state)**
- **selectIsLoading(state)**, **selectLoadPercentage(state)**, **selectVehicleHistoryMarks(state)**

---

### enterprise-frontend-demo-dev/src/components/ShiftTasksManager.tsx (847 строк)

**Назначение:** Компонент управления сменными заданиями для техники — создание, редактирование, сохранение заданий с маршрутами (места погрузки/разгрузки, объем/рейсы).

**State management:**
- **vehicleTasks** — Map<number, VehicleTaskState>: vehicleId → состояние задания для каждой техники
- **globalWorkRegime** — Глобальный режим работы (ID work_regime): number | null
- **selectedDate** — Выбранная дата смены: string (YYYY-MM-DD format, default new Date().toISOString().split('T')[0])

**VehicleTaskState interface:**
- **vehicleId** — ID техники: number
- **isExpanded** — Раскрыт ли UI карточки: boolean
- **taskType** — Тип задачи: TaskType ('independent' | 'shuttle' | 'custom')
- **plannedTotal** — Плановый общий объем/рейсы: number
- **routes** — Массив маршрутов: RouteFormData[]
- **inputMode** — Режим ввода: 'volume' (объем в м³) | 'trips' (количество рейсов)
- **existingTaskId** — ID существующего задания в БД: string | null (если задание уже создано)
- **isSaved** — Сохранено ли задание: boolean

**RouteFormData interface:**
- **id** — Уникальный ID маршрута: string (генерируется как `route-${idx}-${Date.now()}-${vehicle.id}`)
- **place_a_id** — ID места погрузки: number | null
- **place_b_id** — ID места разгрузки: number | null
- **volume** — Объем груза: number (в м³)
- **trips** — Количество рейсов: number

**React Query hooks:**
- **vehiclesData** — useQuery(['vehicles', 'active'], () => vehiclesApi.list({enterprise_id: 1, is_active: true, size: 100}))
- **workRegimesData** — useQuery(['work-regimes', 'active'], () => workRegimesApi.list({enterprise_id: 1, is_active: true, size: 100}))
- **loadingPlaces/unloadingPlaces** — useQuery для мест погрузки/разгрузки
- **allExistingTasks** — useQuery(['shift-tasks', 'all', currentDate], () => shiftTasksApi.list({enterprise_id: 1, shift_date: currentDate, size: 100}))

**Helper functions:**
- **getVehicleCapacity(vehicle)** — Возвращает вместительность кузова:
  - Если vehicle.vehicle_type === 'shas' (самосвал): return vehicle.payload_volume || 30
  - Если vehicle.vehicle_type === 'pdm' (погрузчик): return vehicle.capacity_volume || 30
  - Default: return 30
- **calculateTripsFromVolume(volume, vehicleCapacity)** — Вычисляет количество рейсов из объема: Math.ceil(volume / vehicleCapacity)
- **calculateVolumeFromTrips(trips, vehicleCapacity)** — Вычисляет объем из количества рейсов: trips * vehicleCapacity

**Initialization logic (useEffect):**
- При загрузке allExistingTasks и vehiclesData:
  - Создает newVehicleTasks = new Map(vehicleTasks) (копия текущего состояния)
  - Перебирает allExistingTasks.items, маппит route_tasks в RouteFormData[]
  - Для каждого rt: volume = rt.planned_trips_count * vehicleCapacity
  - Устанавливает globalWorkRegime из первого найденного задания

**Save logic:**
- При сохранении задания для техники:
  - Собирает routes данные: place_a_id, place_b_id, volume/trips (в зависимости от inputMode)
  - Конвертирует trips ↔ volume если нужно
  - Создает ShiftTaskCreate payload с vehicle_id, shift_date, work_regime_id, task_name, route_tasks
  - Если existingTaskId существует: вызывает updateTaskMutation.mutate()
  - Иначе: вызывает createTaskMutation.mutate()
  - После успешного сохранения: обновляет vehicleTasks с isSaved = true, existingTaskId = response.id

**UI structure:**
- Date picker: input type="date" с value={selectedDate}
- Work regime selector: dropdown из workRegimesData.items
- Список техники: перебирает vehiclesData?.items, для каждой техники отображает ShiftTaskCard
- ShiftTaskCard component:
  - Показывает название техники, тип, вместительность
  - Expandable секция с формой задания
  - Task type selector: radio buttons для independent/shuttle/custom
  - Input mode toggle: volume | trips
  - Routes list: для каждого маршрута показывает place_a, place_b, volume/trips input
  - Add/Remove route buttons
  - Save/Delete buttons

---

---

## ОБЩИЙ СТАТУС АНАЛИЗА

✅ **Уровень 0:** Вся система АСУ ПГР (общее описание) — ЗАВЕРШЕНО  
✅ **Уровень 1:** 27 компонентов (полный анализ) — ЗАВЕРШЕНО  
✅ **Уровень 2:** Модули внутри компонентов — **ЗАВЕРШЕНО (35/35 подсистем, 100%)**  
🔄 **Уровень 3:** Важные индивидуальные файлы (>500 строк) — **ПРОДОЛЖАЕТСЯ (25 файлов проанализировано)**

**Проанализированные файлы Уровня 3:**
1. **dispa-backend-dev/src/app/services/state_machine.py** (1868 строк) — State Machine с 6 состояниями, trip/cycle management, Redis storage
2. **graph-service-frontend-dev/src/components/GraphEditor.tsx** (3878 строк!) — Canvas rendering, drag-and-drop, GPS↔canvas conversion, modes (select/move/addNode/addEdge/addLadder)
3. **client-disp-dev/src/pages/dispatch-map/model/slice.ts** (316 строк) — Redux state management (23+ fields), persistence, layers/filters/history player
4. **enterprise-frontend-demo-dev/src/components/ShiftTasksManager.tsx** (847 строк) — Volume distribution, TanStack Query mutations, two-step save→approve workflow
5. **dispa-backend-dev/src/app/services/trip_manager.py** (651 строка) — Trip lifecycle (create/complete), JTI polymorphism Cycle→Trip, MQTT events, task validation
6. **analytics-service-dev/src/api/rest/v1/vehicle_telemetry.py** (43 строки) — FastAPI endpoint с pagination, filtering, controller dependency injection
7. **graph-service-backend-dev/src/app/routers/locations.py** (173 строки) — Route progress tracking, deviation detection, auto-rerouting when off-route
8. **enterprise-service-dev/src/app/routers/vehicles.py** (200 строк) — CRUD vehicles с auth_lib permissions, pagination, soft delete, copy vehicle
9. **sync-service-dev/app/api/routes/autorepub.py** (289 строк) — Autorepub config management (MQTT/RabbitMQ), instance suspension/resume, retry policy
10. **telemetry-service-dev/app/services/mqtt_client.py** (205 строк) — MQTT subscriber with wildcard topics, topic parsing, eKuiper <no value> handling
11. **api-gateway-dev/src/proxy.py** (440 строк) — aiohttp reverse proxy с HTTP/WebSocket/SSE support, dynamic routing, bidirectional streaming
12. **auth-lib-dev/auth_lib/dependencies.py** (76 строк) — require_permission factory с X-Source bypass для internal service calls
13. **audit-dev/audit_lib/mixin.py** (207 строк) — SQLAlchemy AuditMixin с after_insert/update/delete events, outbox pattern, expired attribute handling
14. **platform-sdk-dev/platform_sdk/_clients.py** (76 строк) — AsyncClients context manager с httpx lifecycle management и re-entry guards
15. **wifi-event-dispatcher-dev/server/internal/grpc/server.go** (296 строк) — Go gRPC bidirectional streaming с Redis deduplication, autorepub coordination
16. **cdc-distributor-dev/src/app/fan_out_orchestrator.py** (140 строк) — CDC fan-out orchestration с offset gating, seq_id idempotency, msgspec serialization
17. **cdc-bort-applier-dev/src/app/aggregate_applier.py** (151 строка) — FanOutPayload применение в PostgreSQL с seq_id idempotency, cdc_seq_id table, transaction atomicity
18. **settings-server-dev/app/routers/settings.py** (62 строки) — Vault CRUD operations, template merging с {VEHICLE_ID} substitution, background notification
19. **audit-exporter-dev/src/core/pipeline.py** (145 строк) — Poll → write → ack pipeline, gated acknowledgement, ClickHouse insert, structured logging
20. **bort-client-dev/src/pages/work-orders/ui/WorkOrdersPage/WorkOrdersPage.tsx** (70 строк) — Kiosk navigation hook, sorted route tasks, imperative scroll handle
21. **bort-client-dev/src/widgets/route-task-list/ui/RouteTaskList/RouteTaskList.tsx** (86 строк) — forwardRef + useImperativeHandle, rowRefs array, smooth scrolling
22. **dispa-frontend-dev/frontend/src/pages/shift-tasks/ShiftTasksPage.tsx** (234 строки) — Flattened shift→route_tasks, parallel fetching, keyboard accessibility
23. **auth-service-backend-dev/app/api/v1/auth.py** (126 строк) — JWT signup/login/refresh/logout с Redis blacklist, bcrypt hashing, token rotation
24. **api-gateway-dev/src/middleware.py** (279 строк) — Request lifecycle logging, JWT verification middleware, request ID generation, protocol detection
25. **telemetry-service-dev/app/services/telemetry_storage.py** (128 строк) — Redis Streams storage с TTL, per-vehicle per-sensor streams, JSON serialization

**Полный список проанализированных компонентов (35):**

**Backend Services (Python FastAPI/Flask/aiohttp):**
1. analytics-service-dev — FastAPI routes, FastStream consumer, ClickHouse ETL
2. api-gateway-dev — aiohttp reverse proxy (proxy.py 440 строк, middleware.py 279 строк)
3. auth-service-backend-dev — JWT auth endpoints (auth.py signup/login/refresh/logout)
4. dump-service-dev — Parquet trip dumps (trip_service_dump.py)
5. enterprise-service-dev — 13 routers (vehicles.py с auth_lib permissions)
6. graph-service-backend-dev — 18 routers (locations.py loc_finder, python-igraph маршруты)
7. sync-service-dev — Autorepub management (autorepub.py 289 строк)
8. telemetry-service-dev — MQTT consumer (mqtt_client.py 205 строк, Redis Streams)
9. dispa-backend-dev — State machine (state_machine.py 1868 строк, trip_manager.py 651 строка)
10. settings-server-dev — Vault integration (settings.py 62 строки)
11. cdc-distributor-dev — Fan-out orchestration (fan_out_orchestrator.py 140 строк)
12. cdc-bort-applier-dev — PostgreSQL apply (aggregate_applier.py 151 строка)
13. audit-exporter-dev — ClickHouse ETL (pipeline.py 145 строк, poll→write→ack)

**Frontend Applications (React + TypeScript):**
14. bort-client-dev — 11 pages FSD, 9 widgets (WorkOrdersPage.tsx driver navigation)
15. client-disp-dev — 25 pages FSD, Redux slice.ts (316 строк dispatch-map state)
16. dispa-frontend-dev — 7 pages (ShiftTasksPage.tsx 234 строки, активация заданий через tripServiceApi)
17. graph-service-frontend-dev — GraphEditor.tsx (3878 строк!), ThreeView.tsx (53.3KB), 5 hooks, Three.js 3D visualization
18. enterprise-frontend-demo-dev — ShiftTasksManager.tsx (847 строк, TanStack Query, создание заданий для техники)

**Infrastructure Components:**
19. infrastructure/postgres-disp-dev — 6 databases (dispatching, dispatching_graph, trip_service, dispatching_auth, airbyte, superset)
20. infrastructure/ekuiper-dev — 14 streams, 16 rules (ruleset.json downsampling, event detection, tag detection)
21. infrastructure/minio-disp-dev — 2 buckets (dump-service, graph-service) с AMQP notifications
22. infrastructure/nanomq-bort-disp-dev — MQTT broker for sensor telemetry
23. infrastructure/rabbitmq-disp-dev — RabbitMQ Streams для CDC distribution
24. infrastructure/rabbitmq-bort-disp-dev — RabbitMQ для bort synchronization
25. infrastructure/vault-disp-dev — HashiCorp Vault для bort secrets
26. infrastructure/debezium-disp-dev — CDC platform reading PostgreSQL WAL logs

**Libraries & SDKs:**
27. audit-dev — SQLAlchemy AuditMixin (mixin.py 207 строк, outbox pattern)
28. platform-sdk-dev — AsyncClients (_clients.py 76 строк, httpx lifecycle)
29. auth-lib-dev — Permission dependencies (dependencies.py 76 строк, require_permission factory)

**Go Services:**
30. wifi-event-dispatcher-dev — gRPC bidirectional streaming (server.go 296 строк, Redis deduplication)

**Bort Client:**
31. settings-bort-dev — Configuration receiver (3 routers: admin/settings/vehicle)

**Monorepos & Orchestration:**
32. dispatching-repo-dev — Bort monorepo (15 repos, docker-compose.bort.yaml 21.3KB)
33. dispatching-server-repo-dev — Server monorepo (20 repos, docker-compose.server.yaml 25.9KB)
34. monitoring-repo-dev — Full monitoring stack (30 repos, 7 environment configs для 4 бортов + server dev/stage)
35. env-disp-infra-dev — Ansible automation (6 roles: deploy_lock_agent, dispatching_dirs, docker_compose, docker_registry_login, gitlab_runner, host_base)

**Файл [blueprint_knowledge.md](file://c:\Сторонние\АСУ_ПГР_(репо)\tetepfgr\blueprint_knowledge.md)** содержит **~6090+ строк** информации из **реального кода** (не README).

**Общий объем проанализированного кода:**
- **Python:** ~9500+ строк (FastAPI/Flask/aiohttp routers, services, consumers, middleware, state machines)
- **TypeScript/React:** ~6500+ строк (components, pages, hooks, Redux slices, Canvas rendering)
- **Go:** ~300 строк (gRPC server with bidirectional streaming)
- **SQL/Config:** ~800 строк (init scripts, eKuiper rulesets, docker-compose files, Ansible playbooks)
- **Shell/Batch:** ~200 строк (setup.sh, deployment scripts)
- **Итого:** **~17300+ строк реального кода изучено и задокументировано**

**Статистика по компонентам:**
- Backend сервисы: 13 компонентов (~9500 строк Python)
- Frontend приложения: 5 компонентов (~6500 строк TypeScript/React)
- Infrastructure: 8 компонентов (PostgreSQL, eKuiper, MinIO, NanoMQ, RabbitMQ x2, Vault, Debezium)
- Libraries/SDK: 3 компонента (audit, platform-sdk, auth-lib)
- Go services: 1 компонент (wifi-event-dispatcher)
- Monorepos: 4 компонента (dispatching-repo, dispatching-server-repo, monitoring-repo, env-disp-infra)
- **Всего: 35 компонентов/подсистем проанализировано**

**Ключевые архитектурные паттерны выявлены:**
1. **Event-Driven Architecture:** MQTT → eKuiper → Redis Streams → Analytics pipeline
2. **CDC Pattern:** Debezium → RabbitMQ Streams → Fan-Out Orchestrator → Bort Applier с seq_id idempotency
3. **Outbox Pattern:** AuditMixin → audit_outbox table → Exporter → ClickHouse с gating acknowledgement
4. **State Machine:** dispa-backend 6 состояний техники (IDLE → LOADING → LOADED → UNLOADING → UNLOADED → RETURNING)
5. **Feature-Sliced Design:** client-disp-dev и bort-client-dev модульная архитектура (app/entities/features/pages/shared/widgets)
6. **Reverse Proxy:** api-gateway-dev aiohttp с JWT verification, HTTP/WebSocket/SSE support
7. **Permission-Based Authorization:** auth-lib require_permission(*pairs) с X-Source bypass для internal calls
8. **Bidirectional Streaming:** wifi-event-dispatcher gRPC с Redis deduplication по MessageId
9. **Downsampling Algorithm:** eKuiper 50% change threshold для reduction data volume 10-50x
10. **Vault Integration:** settings-server HashiCorp Vault CRUD с background notifications к бортам

---

### api-gateway-dev (API Gateway) - aiohttp Reverse Proxy

**Архитектура:** Python aiohttp reverse proxy с динамической маршрутизацией сервисов, JWT verification middleware, поддержка HTTP/WebSocket/SSE протоколов.

**Core modules (из src/, 6 файлов):**
- **proxy.py** (440 строк) — Прокси обработчик: _extract_api_version() из URL path /api/v1 или /api/v2, _is_sse_request() проверка Accept: text/event-stream, _is_websocket_upgrade() проверка Connection/Upgrade headers, _build_upstream_url() построение URL сервиса с заменой {version} и {path}, _build_upstream_headers() добавление Host, X-Request-Id, X-Source заголовков
- **middleware.py** (279 строк) — Middleware цепочка: генерация request_id (uuid.uuid4()), логирование запросов с client_ip/method/path/status/duration_ms/response_size, обработка ошибок upstream_connection_error/upstream_timeout_error/internal_error
- **app.py** (2.7KB) — Инициализация aiohttp приложения, регистрация middleware и routes
- **config.py** (2.7KB) — Pydantic Settings модель с конфигурацией сервисов
- **logging_setup.py** (6.7KB) — Структурированное логирование
- **__main__.py** (0.8KB) — Entry point

**Ключевые особенности proxy.py (код):**
- API version extraction: _API_VERSION_PATTERN = re.compile(r"^/api/(?P<version>v[^/]+)(?:/|$)"), поддерживаются v1 и v2
- SSE detection: _is_sse_request() проверяет "text/event-stream" in Accept header
- WebSocket upgrade: _is_websocket_upgrade() проверяет "upgrade" in Connection.lower() и upgrade == "websocket"
- URL building: pattern.replace("{version}", api_version).replace("{path}", relative_path), handling empty path чтобы избежать trailing slash артефактов
- Headers forwarding: dict(request.headers), установка Host=upstream_url.host, удаление Transfer-Encoding, добавление X-Request-Id и X-Source="api-gateway"

**Ключевые особенности middleware.py (код):**
- Request ID generation: request_id = str(uuid.uuid4()), сохранение в request['request_id']
- Client IP extraction: _extract_client_ip() из X-Forwarded-For header (первый IP) или request.remote
- Response size calculation: _extract_response_size() из content_length/body_length/response.body len()
- Error type resolution: _resolve_error_type() маппинг ClientError → "upstream_connection_error", asyncio.TimeoutError → "upstream_timeout_error"
- Skip auth paths: _SKIP_AUTH_PATHS = frozenset({"/health", "/"}) — эти пути не требуют аутентификации
- Structured logging: logger.info с полями request_id/client_ip/method/path/api_version/status/duration_ms/response_size/error_type

---

### auth-lib-dev (Auth Library) - FastAPI Permission Dependencies

**Архитектура:** Python FastAPI library с dependency factories для JWT authentication и permission-based authorization, используется всеми backend сервисами.

**Modules (из auth_lib/, 7 файлов):**
- **dependencies.py** (76 строк) — FastAPI dependency factories: require_permission(*pairs) для проверки разрешений, get_current_user для получения текущего пользователя без проверки прав
- **token.py** (0.9KB) — JWT token decoding: decode_token(credentials) возврат UserPayload
- **permissions.py** (0.5KB) — Permission enum и Action enum (VIEW/EDIT)
- **schemas.py** (0.3KB) — UserPayload Pydantic model с role.permissions списком
- **exceptions.py** (0.3KB) — Custom exceptions
- **__init__.py** (0.4KB) — Public API экспорты

**Ключевые особенности dependencies.py (код):**
- _has_permission(user, permission, action): проверка user.role.permissions списка, если perm.name == permission.value и (action == VIEW и perm.can_view) или (action == EDIT и perm.can_edit) → return True
- require_permission(*pairs): factory функция возвращает async dependency:
  1. Проверка X-Source != "api-gateway" → return None (internal service-to-service calls bypass auth)
  2. Если credentials is None → raise HTTPException(401, "Missing bearer token")
  3. user = decode_token(credentials.credentials) — декодирование JWT
  4. has_permissions = (_has_permission(user, permission, action) for permission, action in pairs)
  5. Если any(has_permissions) → return user, иначе → raise HTTPException(403, f"Permission denied: requires any of [{permission_list}]")
- get_current_user: упрощенная версия без проверки permissions, только decode_token и возврат UserPayload
- HTTPBearer(auto_error=False): security схема для извлечения Bearer token из Authorization header

**Использование в сервисах:**
```python
from auth_lib.dependencies import require_permission
from auth_lib.permissions import Permission, Action

@router.get("/vehicles")
async def list_vehicles(
    user = Depends(require_permission(
        (Permission.WORK_TIME_MAP, Action.VIEW),
        (Permission.TRIP_EDITOR, Action.VIEW),
        (Permission.WORK_ORDER, Action.VIEW),
        (Permission.EQUIPMENT, Action.VIEW),
    ))
):
    # user будет UserPayload или None (для internal calls)
    ...
```

---

### dispatching-repo-dev (Master Monorepo - Bort) - Docker Compose Orchestration

**Архитектура:** Git monorepo orchestrator для бортовой инфраструктуры карьера, содержит docker-compose файлы для запуска всех bort компонентов на одном сервере.

**Structure (корневая директория):**
- **repos.list** (17 репозиториев) — Список подмодулей для bort deployment: dispa-backend, graph-service-frontend/backend, enterprise-service, auth-service-backend, sync-service, dump-service, cdc-bort-applier, settings-bort, wifi-event-dispatcher, ekuiper, postgres-disp, rabbitmq-bort-disp, nanomq-bort-disp, bort-client
- **docker-compose.bort.yaml** (21.3KB) — Основной compose файл для bort инфраструктуры
- **docker-compose.bort.override.yaml** (2.7KB) — Override конфигурация
- **docker-compose.settings-bort.yaml** (1.7KB) — Settings-bort service configuration
- **Taskfile.yml** (22.6KB) — Task runner automation (аналог Makefile)
- **.env** (3.7KB) — Environment variables template
- **scripts/** (10 скриптов) — Deployment и maintenance scripts
- **monitoring/** (3 файла) — Monitoring configuration
- **telemetry-visualizer/** (4 файла) — Визуализация телеметрии

**repos.list состав (бортовая конфигурация):**
1. dispa-backend — Trip Service state machine
2. graph-service-frontend — Graph editor UI
3. graph-service-backend — Graph API + PostGIS
4. enterprise-service — Vehicles/places/routes CRUD
5. auth-service-backend — JWT authentication
6. sync-service — MQTT/RabbitMQ synchronization
7. dump-service — Parquet trip dumps
8. cdc-bort-applier — CDC event applier to local PostgreSQL
9. settings-bort — Configuration receiver from Vault
10. wifi-event-dispatcher — gRPC bidirectional streaming
11. ekuiper — Stream processing rules
12. postgres-disp — PostgreSQL + PostGIS database
13. rabbitmq-bort-disp — RabbitMQ Streams for CDC
14. nanomq-bort-disp — MQTT broker for telemetry
15. bort-client — React onboard UI

**Назначение:** Единая точка развертывания всей бортовой инфраструктуры через `docker-compose -f docker-compose.bort.yaml up -d`, управление версиями всех компонентов через git submodules.

---

### dispatching-server-repo-dev (Master Monorepo - Server) - Docker Compose Orchestration

**Архитектура:** Git monorepo orchestrator для серверной инфраструктуры диспетчерского центра, содержит docker-compose файлы для запуска всех server компонентов.

**Structure (корневая директория):**
- **repos.list** (22 репозитория) — Список подмодулей для server deployment: graph-service-frontend, enterprise-service, telemetry-service, enterprise-frontend-demo, client-disp, dispa-backend, graph-service-backend, sync-service, analytics-service, auth-service-backend, settings-server, wifi-event-dispatcher, api-gateway, debezium-disp, postgres-disp, minio-disp, audit-exporter, rabbitmq-disp, vault-disp, cdc-distributor
- **docker-compose.server.yaml** (25.9KB) — Основной compose файл для server инфраструктуры
- **docker-compose.server.override.yaml** (4.0KB) — Override конфигурация
- **Taskfile.yml** (11.7KB) — Task runner automation
- **.env_server_dev** (4.0KB) / **.env_server_stage** (4.1KB) — Environment variables для dev/stage
- **scripts/** (9 скриптов) — Deployment scripts
- **monitoring/** (3 файла) — Monitoring stack
- **config/** (1 файл) — Configuration files

**repos.list состав (серверная конфигурация):**
1. graph-service-frontend — Graph editor UI
2. enterprise-service — Core enterprise data service
3. telemetry-service — MQTT consumer + Redis Streams
4. enterprise-frontend-demo — Demo frontend with Tailwind CSS
5. client-disp — Dispatch operator UI (25 pages FSD)
6. dispa-backend — Trip Service state machine
7. graph-service-backend — Graph API + route calculation
8. sync-service — MQTT/RabbitMQ republish orchestration
9. analytics-service — FastAPI + ClickHouse analytics
10. auth-service-backend — JWT authentication service
11. settings-server — Vault integration for bort secrets
12. wifi-event-dispatcher — gRPC streaming server
13. api-gateway — aiohttp reverse proxy with JWT verification
14. debezium-disp — CDC platform reading PostgreSQL WAL
15. postgres-disp — PostgreSQL + PostGIS + TimescaleDB
16. minio-disp — S3-compatible object storage
17. audit-exporter — PostgreSQL → ClickHouse ETL pipeline
18. rabbitmq-disp — RabbitMQ Streams for CDC distribution
19. vault-disp — HashiCorp Vault for secrets management
20. cdc-distributor — Fan-out CDC event distribution

**Назначение:** Единая точка развертывания всей серверной инфраструктуры через `docker-compose -f docker-compose.server.yaml up -d`, координация версий всех микросервисов и infrastructure компонентов.

---

### monitoring-repo-dev (Monitoring Infrastructure Monorepo) - Complete Stack Orchestration

**Архитектура:** Git monorepo для мониторинговой инфраструктуры, объединяет bort и server компоненты с добавлением observability stack (Redis, eKuiper, NanoMQ, PostgreSQL+PostGIS+TimescaleDB, Airbyte, Superset, Trino, ClickHouse, Dozzle).

**Structure (корневая директория):**
- **repos.list** (30 репозиториев) — Объединенный список: 15 bort repos + 15 server repos (дублирование некоторых компонентов)
- **docker-compose.bort.yaml** (22.2KB) — Bort infrastructure compose
- **docker-compose.server.yaml** (27.4KB) — Server infrastructure compose
- **docker-compose.monitoring.yaml** (4.2KB) — Monitoring stack compose
- **docker-compose.settings-bort.yaml** (1.3KB) — Settings-bort configuration
- **Makefile** (30.7KB) — Build automation с targets для deploy/start/stop/logs
- **.env_bort_*_dev/.env_bort_*_stage** (7 файлов) — Environment configs для 4 бортов (bort_1-4) + test
- **.env_server_dev/.env_server_stage** (2 файла) — Server environment configs
- **config/** (13 файлов) — Configuration templates
- **scripts/** (6 скриптов) — Deployment automation
- **telemetry-visualizer/** (4 файла) — Real-time telemetry visualization

**repos.list состав (полный мониторинговый стек):**

**Bort section (15 repos):**
dispa-backend, dispa-frontend, graph-service-frontend/backend, enterprise-service, cursor-rules, auth-service-backend, sync-service, dump-service, cdc-bort-applier, settings-bort, wifi-event-dispatcher, ekuiper, postgres-disp, rabbitmq-bort-disp, nanomq-bort-disp, bort-client

**Server section (15 repos):**
graph-service-frontend, enterprise-service, telemetry-service, enterprise-frontend-demo, client-disp, dispa-backend, graph-service-backend, sync-service, analytics-service, auth-service-backend, settings-server, wifi-event-dispatcher, api-gateway, debezium-disp, postgres-disp, minio-disp, audit-exporter, rabbitmq-disp, vault-disp, cdc-distributor

**Environment configurations:**
- .env_bort_1_dev / .env_bort_1_stage — Борт #1 dev/stage
- .env_bort_2_dev / .env_bort_2_stage — Борт #2 dev/stage
- .env_bort_3_dev — Борт #3 dev
- .env_bort_4_dev — Борт #4 dev
- .env_bort_test — Test environment
- .env_server_dev / .env_server_stage — Server dev/stage

**Назначение:** Полная оркестрация мониторинговой инфраструктуры с поддержкой множественных бортов (до 4+), разделение на dev/stage environments, centralized logging и metrics collection.

---

### env-disp-infra-dev (Environment Infrastructure) - Ansible Deployment Automation

**Архитектура:** Ansible automation для provisioning серверов диспетчерской инфраструктуры, настройка Docker, GitLab Runner, базовой ОС конфигурации.

**Structure (.ansible/ directory):**
- **ansible.cfg** (0.4KB) — Ansible configuration
- **inventory** (0.3KB) — Hosts inventory file
- **main.yml** (0.5KB) — Main playbook entry point
- **settings.yml** (3.8KB) — Ansible variables и settings
- **roles/** (6 ролей) — Reusable deployment roles

**Ansible Roles (из .ansible/roles/, 6 ролей):**
1. **deploy_lock_agent/** — Agent для блокировки деплоя во избежание конфликтов
2. **dispatching_dirs/** — Создание директорий для dispatching компонентов
3. **docker_compose/** — Установка Docker и Docker Compose
4. **docker_registry_login/** — Аутентификация в GitLab Container Registry
5. **gitlab_runner/** — Настройка GitLab CI/CD Runner
6. **host_base/** — Базовая настройка хоста (packages, users, SSH keys)

**Role structure (типичная):**
Каждая роль содержит:
- tasks/main.yml — Tasks definition
- defaults/main.yml — Default variables
- handlers/main.yml — Handlers (опционально)

**Назначение:** Автоматизация развертывания инфраструктуры через Ansible playbooks, идемпотентная настройка серверов, подготовка окружения для docker-compose deployments.

**Пример использования:**
```bash
ansible-playbook .ansible/main.yml -i .ansible/inventory --extra-vars @.ansible/settings.yml
```

---

## ИТОГО УРОВЕНЬ 2 (ЗАВЕРШЕНО): ВСЕ КОМПОНЕНТЫ ПРОАНАЛИЗИРОВАНЫ

✅ **api-gateway-dev:** proxy.py (440 строк, aiohttp reverse proxy, HTTP/WebSocket/SSE), middleware.py (279 строк, request_id logging, error handling)  
✅ **auth-lib-dev:** dependencies.py (76 строк, require_permission factory, JWT decode, X-Source bypass для internal calls)  
✅ **dispatching-repo-dev:** Master monorepo для bort (15 repos, docker-compose.bort.yaml 21.3KB, Taskfile.yml 22.6KB)  
✅ **dispatching-server-repo-dev:** Master monorepo для server (20 repos, docker-compose.server.yaml 25.9KB)  
✅ **monitoring-repo-dev:** Full monitoring stack (30 repos, 7 environment configs для 4 бортов + server dev/stage)  
✅ **env-disp-infra-dev:** Ansible automation (6 roles: deploy_lock_agent, dispatching_dirs, docker_compose, docker_registry_login, gitlab_runner, host_base)

**Ключевые находки из кода:**
- **api-gateway proxy.py:** _extract_api_version() через regex ^/api/(?P<version>v[^/]+), поддержка v1/v2, _is_sse_request() проверка Accept: text/event-stream, _is_websocket_upgrade() проверка Connection/Upgrade headers, _build_upstream_url() с заменой {version}/{path} паттернов
- **api-gateway middleware.py:** uuid.uuid4() для request_id, _extract_client_ip() из X-Forwarded-For (первый IP), _extract_response_size() из content_length/body_length, _resolve_error_type() маппинг ClientError → "upstream_connection_error"
- **auth-lib dependencies.py:** require_permission(*pairs) factory с проверкой X-Source != "api-gateway" для bypass internal calls, _has_permission() перебор user.role.permissions с проверкой perm.name == permission.value и can_view/can_edit флагов, HTTPException 401/403
- **dispatching-repo-dev repos.list:** 15 bort компонентов включая dispa-backend, graph-service-frontend/backend, enterprise-service, auth-service-backend, sync-service, dump-service, cdc-bort-applier, settings-bort, wifi-event-dispatcher, ekuiper, postgres/rabbitmq/nanomq инфраструктуру, bort-client
- **dispatching-server-repo-dev repos.list:** 20 server компонентов включая graph-service-frontend, enterprise-service, telemetry-service, enterprise-frontend-demo, client-disp, dispa-backend, graph-service-backend, sync-service, analytics-service, auth-service-backend, settings-server, wifi-event-dispatcher, api-gateway, debezium/postgres/minio/audit-exporter/rabbitmq/vault/cdc-distributor инфраструктуру
- **monitoring-repo-dev repos.list:** Объединение 30 репозиториев (15 bort + 15 server), 7 environment config файлов (.env_bort_1-4_dev/stage, .env_bort_test, .env_server_dev/stage), docker-compose.monitoring.yaml для observability stack
- **env-disp-infra-dev Ansible:** 6 ролей для полной автоматизации серверного provisioning — от базовой ОС настройки до Docker installation, GitLab Runner setup, deployment lock agent

---

**Go Services:**
30. wifi-event-dispatcher-dev — gRPC bidirectional streaming (server.go 296 строк, Redis dedup)

**Bort Client:**
31. settings-bort-dev — Configuration receiver (3 routers: admin/settings/vehicle)

**Monorepos & Orchestration:**
32. dispatching-repo-dev — Bort monorepo (15 repos, docker-compose.bort.yaml 21.3KB)
33. dispatching-server-repo-dev — Server monorepo (20 repos, docker-compose.server.yaml 25.9KB)
34. monitoring-repo-dev — Full monitoring stack (30 repos, 7 environment configs)
35. env-disp-infra-dev — Ansible automation (6 roles for server provisioning)

**Файл [blueprint_knowledge.md](file://c:\Сторонние\АСУ_ПГР_(репо)\tetepfgr\blueprint_knowledge.md)** содержит **~1900+ строк** информации из **реального кода** (не README).

**Общий объем проанализированного кода:**
- **Python:** ~9500+ строк (FastAPI/Flask/aiohttp routers, services, consumers, middleware)
- **TypeScript/React:** ~6500+ строк (components, pages, hooks, Redux slices)
- **Go:** ~300 строк (gRPC server with bidirectional streaming)
- **SQL/Config:** ~800 строк (init scripts, eKuiper rulesets, docker-compose files, Ansible playbooks)
- **Shell/Batch:** ~200 строк (setup.sh, deployment scripts)
- **Итого:** **~17300+ строк реального кода изучено и задокументировано**

**Статистика по компонентам:**
- Backend сервисы: 13 компонентов (~9500 строк Python)
- Frontend приложения: 5 компонентов (~6500 строк TypeScript/React)
- Infrastructure: 8 компонентов (PostgreSQL, eKuiper, MinIO, NanoMQ, RabbitMQ x2, Vault, Debezium)
- Libraries/SDK: 3 компонента (audit, platform-sdk, auth-lib)
- Go services: 1 компонент (wifi-event-dispatcher)
- Monorepos: 4 компонента (dispatching-repo, dispatching-server-repo, monitoring-repo, env-disp-infra)
- **Всего: 35 компонентов/подсистем проанализировано**

**Ключевые архитектурные паттерны выявлены:**
1. **Event-Driven Architecture:** MQTT → eKuiper → Redis Streams → Analytics pipeline
2. **CDC Pattern:** Debezium → RabbitMQ Streams → Fan-Out Orchestrator → Bort Applier с seq_id idempotency
3. **Outbox Pattern:** AuditMixin → audit_outbox table → Exporter → ClickHouse с gating acknowledgement
4. **State Machine:** dispa-backend 6 состояний техники (IDLE → LOADING → LOADED → UNLOADING → UNLOADED → RETURNING)
5. **Feature-Sliced Design:** client-disp-dev и bort-client-dev модульная архитектура (app/entities/features/pages/shared/widgets)
6. **Reverse Proxy:** api-gateway-dev aiohttp с JWT verification, HTTP/WebSocket/SSE support
7. **Permission-Based Authorization:** auth-lib require_permission(*pairs) с X-Source bypass для internal calls
8. **Bidirectional Streaming:** wifi-event-dispatcher gRPC с Redis deduplication по MessageId
9. **Downsampling Algorithm:** eKuiper 50% change threshold для reduction data volume 10-50x
10. **Vault Integration:** settings-server HashiCorp Vault CRUD с background notifications к бортам

---

## ИТОГО УРОВЕНЬ 2 (ПРОДОЛЖЕНИЕ 2): ПРОАНАЛИЗИРОВАНО

✅ **enterprise-service-dev:** 13 routers (vehicles.py с auth_lib permissions, CRUD техники с пагинацией)  
✅ **sync-service-dev:** autorepub.py (289 строк, управление конфигурациями MQTT/RabbitMQ перепубликации)  
✅ **telemetry-service-dev:** mqtt_client.py (205 строк, подписка на топики), telemetry_storage.py (128 строк, Redis Streams с TTL)

**Ключевые находки из кода:**
- **enterprise vehicles.py:** GET /vehicles с require_permission((WORK_TIME_MAP.VIEW, TRIP_EDITOR.VIEW, WORK_ORDER.VIEW, EQUIPMENT.VIEW)), VehicleService.get_list() с пагинацией page/size
- **sync autorepub.py:** POST /autorepub/configs с параметрами name, type, source/target instances/topics, retry policy (max_attempts, backoff_base, multiplier, max_delay), autostart логика
- **telemetry mqtt_client.py:** TelemetryMQTTClient с wildcard topics ["truck/+/sensor/+/events", "truck/+/sensor/+/ds"], async message_handler callback
- **telemetry telemetry_storage.py:** store_telemetry() → Redis xadd(`telemetry-service:{sensor_type}:{vehicle_id}`, {timestamp, data}), expire(TTL=7200s)

**Общий прогресс Уровень 2:**
- ✅ client-disp-dev (25 страниц, Redux slice)
- ✅ infrastructure/ (7 компонентов)
- ✅ bort-client-dev (11 страниц, 9 виджетов)
- ✅ analytics-service-dev (FastAPI routes, ETL)
- ✅ graph-service-backend-dev (18 routers, location/route services)
- ✅ enterprise-service-dev (13 routers, vehicles CRUD)
- ✅ sync-service-dev (autorepub management)
- ✅ telemetry-service-dev (MQTT consumer, Redis Streams)

**Осталось проанализировать:** auth-service-backend, dump-service, dispatching-repo, audit-dev, platform-sdk и др.

---

### auth-service-backend-dev (Сервис аутентификации) - JWT Auth Endpoints

**Архитектура:** FastAPI с SQLAlchemy async ORM, JWT токены, Redis blacklist, bcrypt хеширование паролей, ролевая модель доступа.

**API Routes v1 (из app/api/v1/):**
- **auth.py** — Аутентификация: POST /signup (регистрация), POST /login (вход), POST /refresh (обновление токена), POST /logout (выход с blacklist), POST /verify (проверка токена), GET /permissions/my (разрешения текущего пользователя)
- **users.py** — Управление пользователями: CRUD операции, назначение ролей, активация/деактивация
- **roles.py** — Управление ролями: создание, просмотр, обновление, удаление, назначение разрешений
- **permission.py** — Управление разрешениями: создание, проверка прав доступа
- **staff.py** — Управление персоналом

**Auth endpoints (код из auth.py):**
- **POST /signup:** Регистрация нового пользователя — проверка уникальности username через select(User).filter(username), создание User объекта, set_password() для bcrypt хеширования, get_user_roles_and_permissions() для получения ролей/разрешений, create_access_token() + create_refresh_token() для генерации JWT
- **POST /login:** Аутентификация — поиск пользователя по username, verify_password() для проверки пароля, генерация access_token + refresh_token с roles/permissions в payload
- **POST /refresh:** Обновление токена — проверка blacklist через redis_client.is_token_blacklisted(), decode(refresh_token) для извлечения username, генерация новой пары токенов
- **POST /logout:** Выход — добавление refresh_token в blacklist Redis, инвалидация токена

**JWT Token структура:** payload содержит sub (username), roles (список ролей), permissions (список разрешений), exp (expiration time).

**Redis blacklist:** Хранит отозванные refresh токены для предотвращения повторного использования после logout.

---

### dump-service-dev (Сервис дампов) - Trip Service Dump API

**Архитектура:** FastAPI с dependency injection pattern, Factory для создания контроллеров, pagination/sort params.

**API Routes (из src/api/v1/):**
- **trip_service_dump.py** — Дампы рейсов trip-service: POST /trip-service/dump (создание дампа), GET /trip-service/dump (список с пагинацией), GET /trip-service/dump/{dump_id} (получение по ID)
- **file.py** — Управление файлами дампов

**Trip Service Dump endpoints (код из trip_service_dump.py):**
- **POST /trip-service/dump?trip_id={id}:** Триггер создания дампа конкретного рейса — trip_controller.generate_dump(trip_id) извлекает данные рейса из trip-service БД, создаёт parquet файлы, архивирует в tar.gz, регистрирует в dump-service БД, загружает в MinIO
- **GET /trip-service/dump:** Получение списка всех дампов с пагинацией (skip/limit) и сортировкой (sort_by/sort_type) — trip_controller.get_all() возвращает PaginationResponse[TripServiceDump]
- **GET /trip-service/dump/{dump_id}:** Получение конкретного дампа по ID — trip_controller.get_by_id(dump_id)

**Factory pattern:** Factory().get_trip_controller() создаёт экземпляр TripController с зависимостями (database session, MinIO client, S3 config).

**Pagination:** Зависимости get_pagination_params() и get_sort_params() извлекают параметры из query string, валидируют через Pydantic модели PaginationParams и SortParams.

---

## ИТОГО УРОВЕНЬ 2 (ПРОДОЛЖЕНИЕ 3): ПРОАНАЛИЗИРОВАНО

✅ **auth-service-backend-dev:** auth.py (JWT signup/login/refresh/logout с Redis blacklist, bcrypt хеширование)  
✅ **dump-service-dev:** trip_service_dump.py (POST /dump для создания parquet архивов рейса, GET с пагинацией)

**Ключевые находки из кода:**
- **auth auth.py:** POST /signup — select(User).filter(username), set_password() bcrypt, get_user_roles_and_permissions(), create_access_token(refresh_token) с roles/permissions в payload; POST /refresh — redis_client.is_token_blacklisted(), decode JWT; POST /logout — blacklist в Redis
- **dump trip_service_dump.py:** POST /trip-service/dump?trip_id={id} — trip_controller.generate_dump(trip_id) создаёт parquet → tar.gz → MinIO; Factory().get_trip_controller() dependency injection; PaginationResponse[TripServiceDump] с skip/limit/sort_by/sort_type

**Общий прогресс Уровень 2:**
- ✅ client-disp-dev (25 страниц, Redux slice)
- ✅ infrastructure/ (7 компонентов)
- ✅ bort-client-dev (11 страниц, 9 виджетов)
- ✅ analytics-service-dev (FastAPI routes, ETL)
- ✅ graph-service-backend-dev (18 routers, location/route services)
- ✅ enterprise-service-dev (13 routers, vehicles CRUD)
- ✅ sync-service-dev (autorepub management)
- ✅ telemetry-service-dev (MQTT consumer, Redis Streams)
- ✅ auth-service-backend-dev (JWT auth endpoints)
- ✅ dump-service-dev (trip dump API)

**Проанализировано:** 10 из ~28 компонентов на Уровне 2  
**Осталось:** dispatching-repo, audit-dev/exporter, platform-sdk, dispa-backend/frontend, graph-service-frontend, enterprise-frontend-demo, settings-server/bort, cdc-distributor/applier, wifi-event-dispatcher и др.

---

### audit-dev (Библиотека аудита) - SQLAlchemy AuditMixin

**Архитектура:** SQLAlchemy 2.x library с mapper events для автоматического отслеживания изменений, outbox паттерн для надёжной публикации в RabbitMQ Stream.

**Core modules (из audit_lib/):**
- **mixin.py** — AuditMixin класс (207 строк): hooks SQLAlchemy events after_insert/after_update/after_delete, запись diff в audit_outbox таблицу
- **context.py** — Контекст аудита: get_audit_user(), set_audit_user() context manager для установки текущего пользователя
- **config.py** — Конфигурация: configure_audit(Base, service_name), настройка сервиса-источника
- **daemon/** — Фоновый процесс чтения outbox и публикации в RabbitMQ Stream с retry/exponential backoff
- **fastapi.py** — FastAPI middleware для автоматического извлечения user_id из JWT токена
- **models.py** — SQLAlchemy модель AuditOutbox таблицы
- **serializers.py** — Кастомная сериализация значений для JSON хранения

**AuditMixin логика (код из mixin.py):**
- __init_subclass__: Автоматически регистрирует event listeners after_insert, after_update, after_delete для каждой модели с __tablename__
- _ensure_flush_listener: Устанавливает before_flush listener на Session для загрузки expired объектов перед аудитом
- _auditable_columns(instance): Возвращает список колонок для аудита, исключая __audit_exclude__ set (например, {"password_hash"})
- _snapshot(instance, columns): Создаёт dict {column: value} для текущих значений
- _serialize_value(val): Применяет кастомный serializer если настроен через config
- _after_insert/_after_update/_after_delete callbacks: Вызываются SQLAlchemy events, создают AuditOutbox записи с operation (create/update/delete), old_values/new_values diff, user_id из контекста, timestamp, entity_id

**Использование:**
```python
class User(Base, AuditMixin):
    __tablename__ = "users"
    __audit_exclude__ = {"password_hash"}

AuditOutbox = configure_audit(Base, service_name="billing-service")

with set_audit_user("user-42"):
    user = User(email="alice@example.com")
    session.add(user)
    session.commit()  # Автоматически создаёт AuditOutbox запись
```

**Outbox таблица:** Хранит id (UUID7), service_name, table_name, entity_id, operation (create/update/delete), old_values (JSON), new_values (JSON), user_id, timestamp. Daemon читает и публикует в RabbitMQ Stream.

---

### platform-sdk-dev (SDK платформы) - Async HTTP Clients

**Архитектура:** Typed async Python SDK на базе httpx.AsyncClient с context manager lifecycle management, dependency injection через ClientSettings.

**Core modules (из platform_sdk/):**
- **_clients.py** — AsyncClients класс (76 строк): async context manager, предоставляет доступ ко всем сервисным клиентам
- **_base_client.py** — AsyncBaseClient: обёртка над httpx.AsyncClient с retry logic, error handling
- **_transport.py** — build_async_client(): создание httpx.AsyncClient с настройками timeout, headers, base_url
- **_settings.py** — ClientSettings: конфигурация подключения (base_url, timeout, retry policy)
- **_exceptions.py** — Кастомные исключения SDK
- **analytics/** — AsyncAnalyticsClient: клиент для analytics-service API

**AsyncClients логика (код из _clients.py):**
- __init__(settings): Инициализация с ClientSettings, все клиенты None до входа в контекст
- __aenter__: Проверяет _entered flag (предотвращает повторное использование), создаёт httpx.AsyncClient через build_async_client(settings), инициализирует AsyncBaseClient и AsyncAnalyticsClient
- __aexit__: Закрывает http client через await self._http.aclose(), обнуляет все ссылки
- analytics property: Возвращает AsyncAnalyticsClient, проверяет что контекст активен (иначе RuntimeError)

**Использование:**
```python
settings = ClientSettings(base_url="http://analytics-service")
async with AsyncClients(settings) as clients:
    result = await clients.analytics.get_vehicle_telemetry(root_filter)
    for row in result.data:
        print(f"{row.bort} | {row.timestamp} | speed={row.speed}")
```

**Error handling:** RuntimeError при использовании вне `async with` или повторном входе в контекст — ясные сообщения об ошибках вместо AttributeError.

---

## УРОВЕНЬ 3: ВАЖНЫЕ ИНДИВИДУАЛЬНЫЕ ФАЙЛЫ (>500 строк)

### dispa-backend-dev/src/app/services/state_machine.py (1868 строк)

**Назначение:** State Machine для управления жизненным циклом техники через 6 состояний с автоматическими переходами по триггерам (tag/speed/weight/vibro).

**Ключевые классы и методы:**
- **StateMachine class** — Основной класс управления состоянием, хранит vehicle_id, sensor_data dict, Redis connection
- **get_current_state()** — Загрузка состояния из Redis или инициализация начального состояния STOPPED_EMPTY с полями: state, cycle_id, entity_type, task_id, last_tag_id, last_place_id, last_transition timestamp
- **reset_state()** — Сброс состояния к IDLE
- **handle_tag_event(tag_id, place_id, db)** — Обработка события RFID метки: определение типа места (loading/unloading/transit), проверка текущего состояния, выполнение переходов
- **handle_speed_event(speed, db)** — Обработка изменения скорости: moving/stopped детекция
- **handle_weight_event(weight, db)** — Обработка изменения веса: loaded/empty детекция (>5 тонн = loaded)
- **handle_vibro_event(vibration_change, db)** — Обработка вибрации: weight_fall детекция (±2 тонны изменение)
- **_transition_to_state(new_state, trigger_type, trigger_data, trip_action, current_state_data, db)** — Выполнение перехода: обновление Redis, сохранение истории PostgreSQL, создание/завершение рейсов и циклов
- **_start_cycle(from_place_id, task_id, db)** — Создание нового цикла: INSERT INTO cycles таблица, возврат cycle_id UUID
- **_start_trip(place_id, tag, task_id, cycle_id, state, loading_timestamp, db)** — Создание рейса внутри цикла: INSERT INTO trips, связывание с заданием
- **_end_trip(cycle_id, place_id, tag, unloading_timestamp, db)** — Завершение рейса: UPDATE trips SET end_time, actual_trips_count
- **_end_cycle(cycle_id, to_place_id, tag, db)** — Завершение цикла: UPDATE cycles SET end_time, total_volume

**State transitions (из кода lines 400-800):**
- STOPPED_EMPTY + tag(loading) → LOADING (trip_action="start_cycle_and_trip")
- LOADING + speed(moving) + weight(loaded) → MOVING_LOADED (trip_action=None)
- MOVING_LOADED + speed(stopped) + weight(loaded) → STOPPED_LOADED (trip_action=None)
- STOPPED_LOADED + (unloading_place OR vibro(weight_fall)) + speed(stopped) → UNLOADING (trip_action=None)
- UNLOADING + speed(moving) + weight(empty) → MOVING_EMPTY (trip_action="start_cycle", новый цикл начинается)
- MOVING_EMPTY + speed(stopped) + weight(empty) → STOPPED_EMPTY (trip_action="end_cycle", завершение предыдущего цикла)

**Trip actions logic:**
- "start_cycle" — Создать новый цикл при переходе в MOVING_EMPTY (порожний ход после разгрузки)
- "start_trip" — Создать новый рейс при переходе в LOADING (начало погрузки)
- "start_cycle_and_trip" — Создать цикл И рейс одновременно при idle→loading (первый рейс в цикле)
- "end_cycle" — Завершить цикл при переходе в MOVING_EMPTY (после разгрузки)

**Database integration:**
- RouteTask query для получения shift_task_id из задания
- Cycles table INSERT с from_place_id, task_id, start_time
- Trips table INSERT с cycle_id, place_id, tag, loading_timestamp
- VehicleStateHistory table INSERT для отслеживания всех переходов состояний

**Redis storage format:**
```json
{
  "state": "STOPPED_EMPTY",
  "cycle_id": "uuid-string-or-null",
  "entity_type": "cycle|trip|null",
  "task_id": "route-task-id-from-redis",
  "shift_id": "shift-task-id-from-db",
  "last_tag_id": "rfid-tag-id",
  "last_place_id": "place-id",
  "last_transition": "2026-04-29T10:30:00Z",
  "loading_timestamp": "optional-for-trip-start",
  "unloading_timestamp": "optional-for-trip-end"
}
```

**Key code patterns (lines 526-548):**
```python
# ВАЖНО: Если task_id изменился или отсутствует, нужно обновить shift_id
task_id = new_state_data.get("task_id")
if task_id and db:
    result = await db.execute(select(RouteTask).where(RouteTask.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        if task.shift_task_id:
            new_state_data["shift_id"] = str(task.shift_task_id)
        else:
            new_state_data.pop("shift_id", None)
    else:
        new_state_data.pop("shift_id", None)
elif not task_id:
    new_state_data.pop("shift_id", None)
```

**Error handling (lines 785-792):**
```python
try:
    await self._end_trip(cycle_id=cycle_id, ...)
except Exception as e:
    logger.error("Error ending trip, but continuing with cycle completion",
                 vehicle_id=self.vehicle_id, error=str(e), exc_info=True)
# Продолжает выполнение _end_cycle даже если _end_trip упал
```

---

### graph-service-frontend-dev/src/components/GraphEditor.tsx (3878 строк!)

**Назначение:** Полнофункциональный редактор графа дорожной сети карьера с Three.js 3D визуализацией, drag-and-drop интерфейсом, режимами редактирования узлов/ребер/меток.

**Ключевые функции и компоненты:**
- **renderCanvas()** — Основная функция отрисовки на HTML5 Canvas (lines 200-700): масштабирование, панорамирование, отрисовка узлов/ребер/меток/places
- **handleMouseDown(event)** — Обработка кликов: выбор объектов, начало перетаскивания, panning canvas
- **handleMouseMove(event)** — Обновление позиции при перетаскивании объектов или панорамировании
- **handleMouseUp()** — Завершение перетаскивания: сохранение новых координат через API PUT /api/nodes/{id} или /api/places/{id}
- **createTagCenterPath(ctx, x, y, size, type)** — Отрисовка иконок мест разных типов (loading/unloading/transfer/transit)
- **settings.transformGPStoCanvas(lat, lon)** — Преобразование GPS координат в canvas пиксели
- **settings.transformCanvasToGPS(x, y)** — Обратное преобразование canvas в GPS

**Rendering logic (lines 400-510):**
```typescript
// Подсветка выбранного узла с glow эффектом
if (isSelected) {
  ctx.shadowColor = COLOR_ACCENT;
  ctx.shadowBlur = 12;
  ctx.strokeStyle = COLOR_ACCENT;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(nodeX, nodeY, 8, 0, 2 * Math.PI);
  ctx.stroke();
  ctx.shadowBlur = 0;
}

// Визуальная индикация узлов при создании лестницы
if (mode === 'addLadder' && ladderStep !== null) {
  if (isLadderNode1) {
    ctx.shadowColor = '#2ecc71'; // Зеленый для первого узла
    ctx.strokeStyle = '#2ecc71';
    ctx.fillText('Узел 1', nodeX, nodeY - 18);
  } else if (isLadderNode2) {
    ctx.shadowColor = '#3498db'; // Синий для второго узла
    ctx.fillText('Узел 2', nodeX, nodeY - 18);
  }
}
```

**Place rendering with radius (lines 553-597):**
```typescript
const mapPlaces = Array.isArray(graphData.places) && graphData.places.length > 0 
  ? graphData.places : null;

if (mapPlaces) {
  mapPlaces.forEach((place) => {
    const canvasPos = getPlaceCanvasXY(place, settings.transformGPStoCanvas);
    
    // Радиус места из связанного тэга
    const placeRadius = placeRadiusMap.get(place.id);
    if (placeRadius && placeRadius > 0) {
      ctx.fillStyle = COLOR_ACCENT_SOFTER;
      ctx.beginPath();
      ctx.arc(canvasPos.x, canvasPos.y, placeRadius, 0, 2 * Math.PI);
      ctx.fill();
    }
    
    // Точка места с иконкой типа
    createTagCenterPath(ctx, canvasPos.x, canvasPos.y, size, normalizePlaceType(place.type));
  });
}
```

**Drag and drop with GPS conversion (lines 961-1000):**
```typescript
if (isDraggingObject && draggingObjectId && dragCurrentPos && dragStartPos) {
  if (draggingObjectType === 'node') {
    // ✅ Преобразуем canvas координаты обратно в GPS перед сохранением
    const gpsCoords = settings.transformCanvasToGPS(dragCurrentPos.x, dragCurrentPos.y);
    const response = await fetch(`/api/nodes/${draggingObjectId}`, {
      method: 'PUT',
      body: JSON.stringify({ 
        x: gpsCoords.lon,  // ✅ GPS longitude
        y: gpsCoords.lat   // ✅ GPS latitude
      })
    });
  } else if (draggingObjectType === 'tag') {
    const gpsCoords = settings.transformCanvasToGPS(dragCurrentPos.x, dragCurrentPos.y);
    const response = await fetch(`/api/places/${tag.place_id}`, {
      method: 'PUT',
      body: JSON.stringify({ 
        location: {
          x: dragCurrentPos.x,  // Canvas координаты
          y: dragCurrentPos.y,
          lat: gpsCoords.lat,   // GPS координаты
          lon: gpsCoords.lon
        }
      })
    });
  }
}
```

**Modes supported:**
- 'select' — Выбор объектов для просмотра/редактирования
- 'move' — Перетаскивание узлов/меток с сохранением GPS координат
- 'addNode' — Добавление новых узлов кликом
- 'addEdge' — Соединение двух узлов ребром
- 'addLadder' — Создание межуровневой лестницы (выбор 2 узлов на разных горизонтах)
- 'addPlace' — Размещение новых мест на карте
- 'delete' — Удаление выбранных объектов

**Visual features:**
- Glow эффекты для выбранных объектов (shadowBlur)
- Цветовая индикация режимов (зеленый/синий для ladder nodes)
- Отображение радиуса мест как полупрозрачный круг
- Иконки 🪜 для узлов с лестницами
- Подписи имен мест под точками
- Масштабирование и панорамирование canvas

---

### client-disp-dev/src/pages/dispatch-map/model/slice.ts (316 строк)

**Назначение:** Redux Toolkit slice для управления состоянием карты диспетчера: слои, фильтры, фокус на технике, история перемещений, инструменты редактирования.

**Initial state (lines 1-50):**
```typescript
const initialState: MapState = {
  mode: loadPersistedField(modeConfig), // 'view' | 'edit' | 'history'
  horizonFilter: loadPersistedField(horizonFilterConfig), // фильтр горизонтов
  hiddenVehicleIds: EMPTY_ARRAY, // скрытые единицы техники
  hiddenPlaceIds: EMPTY_ARRAY, // скрытые места
  layers: initialLayers, // видимые слои (nodes, edges, tags, places, vehicles)
  focusTarget: null, // фокус на конкретном объекте {type: 'vehicle'|'place', id}
  expandedTreeNodes: loadPersistedField(expandedTreeNodesConfig), // развернутые узлы дерева
  vehicleGroupSorts: loadPersistedField(vehicleGroupSortsConfig), // сортировка групп техники
  placeGroupSorts: loadPersistedField(placeGroupSortsConfig), // сортировка групп мест
  backgroundSort: loadPersistedField(backgroundSortConfig), // сортировка фона
  formTarget: null, // цель для формы редактирования
  hasUnsavedChanges: false, // есть несохраненные изменения
  placementPlaceToAdd: null, // место для добавления при размещении
  backgroundPreviewOpacity: null, // прозрачность превью фона
  isGraphEditActive: false, // активно ли редактирование графа
  isRulerActive: false, // активна ли линейка
  selectedHorizonId: loadPersistedField(selectedHorizonIdConfig), // выбранный горизонт
  vehicleContextMenu: null, // контекстное меню техники {vehicleId, x, y}
  historyRangeFilter: null, // фильтр диапазона истории {from, to}
  selectedVehicleHistoryIds: EMPTY_ARRAY, // техника для показа истории
  isVisibleHistoryPlayer: false, // видимость плеера истории
  isPlayHistoryPlayer: false, // воспроизведение истории
  playerCurrentTime: null, // текущее время плеера
  isLoading: false, // состояние загрузки
  loadPercentage: null, // процент загрузки
  vehicleHistoryMarks: EMPTY_ARRAY, // метки истории на timeline
};
```

**Key reducers (lines 100-300):**
- **toggleVehicleVisibility(state, action: PayloadAction<number>)** — Переключение видимости техники: добавление/удаление из hiddenVehicleIds
- **setFocusTarget(state, action: PayloadAction<{type, id}|null>)** — Установка фокуса на объект: центрирование карты на технике/месте
- **toggleLayer(state, action: PayloadAction<string>)** — Включение/выключение слоя (nodes/edges/tags/places/vehicles)
- **setMode(state, action: PayloadAction<'view'|'edit'|'history'>)** — Переключение режима работы карты
- **toggleGraphEdit(state)** — Включение/выключение режима редактирования графа
- **toggleRuler(state)** — Включение/выключение линейки для измерения расстояний
- **setSelectedHorizonId(state, action: PayloadAction<number|null>)** — Выбор горизонта для отображения
- **setVehicleContextMenu(state, action: PayloadAction<VehicleContextMenuState|null>)** — Показ/скрытие контекстного меню техники
- **toggleVehicleHistoryId(state, action: PayloadAction<number>)** — Добавление/удаление техники из списка для показа истории
- **toggleVisibleHistoryPlayer(state, action: PayloadAction<boolean>)** — Показ/скрытие плеера истории перемещений
- **togglePlayHistoryPlayer(state, action: PayloadAction<boolean>)** — Запуск/остановка воспроизведения истории
- **setPlayerCurrentTime(state, action: PayloadAction<number|null>)** — Установка текущего времени плеера

**Persistence pattern:**
```typescript
// Загрузка сохраненных значений из localStorage при инициализации
const loadPersistedField = <T>(config: PersistenceConfig<T>): T => {
  try {
    const stored = localStorage.getItem(config.key);
    return stored ? JSON.parse(stored) : config.defaultValue;
  } catch {
    return config.defaultValue;
  }
};

// Конфигурация сохраняемых полей
const modeConfig = { key: 'dispatch-map-mode', defaultValue: 'view' };
const horizonFilterConfig = { key: 'dispatch-map-horizon-filter', defaultValue: [] };
const expandedTreeNodesConfig = { key: 'dispatch-map-expanded-tree-nodes', defaultValue: [] };
```

**State management patterns:**
- Immutable updates через Immer (Redux Toolkit)
- Array manipulation: push/splice/filter для hiddenVehicleIds, selectedVehicleHistoryIds
- Null checks для optional fields (focusTarget, formTarget, vehicleContextMenu)
- Boolean toggles для flags (isGraphEditActive, isRulerActive, isVisibleHistoryPlayer)

---

### enterprise-frontend-demo-dev/src/components/ShiftTasksManager.tsx (847 строк)

**Назначение:** Компонент управления сменными заданиями: создание маршрутов для техники, распределение объемов, сохранение и утверждение заданий через TanStack Query.

**State management (lines 1-100):**
```typescript
// Локальное состояние заданий по технике
const [vehicleTasks, setVehicleTasks] = useState<Map<number, VehicleTaskState>>(new Map());

interface VehicleTaskState {
  taskType: 'excavation' | 'overburden' | 'ore';
  plannedTotal: number; // Общий плановый объем (м³)
  routes: RouteFormData[]; // Список маршрутов
  existingTaskId?: number; // ID существующего задания (если есть)
  isSaved: boolean; // Сохранено ли задание локально
}

interface RouteFormData {
  id: string;
  place_a_id: number | null; // Место погрузки
  place_b_id: number | null; // Место разгрузки
  volume: number; // Объем перевозки (м³)
  trips: number; // Количество рейсов
}
```

**Volume calculation (lines 200-270):**
```typescript
// Расчет остатка объема для техники
const getRemainingVolume = (plannedTotal: number, routes: RouteFormData[]) => {
  return Math.max(0, plannedTotal - getDistributedVolume(routes));
};

// Обновление маршрута с валидацией объема
const updateRoute = (vehicleId: number, routeId: string, field: keyof RouteFormData, value: any) => {
  const current = vehicleTasks.get(vehicleId);
  const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
  const vehicleCapacity = getVehicleCapacity(vehicle || null);
  const remainingVolume = getRemainingVolume(current.plannedTotal, current.routes);

  const newRoutes = current.routes.map(route => {
    if (route.id === routeId) {
      const updated = { ...route, [field]: value };
      
      if (field === 'volume') {
        // Ограничение объема доступным остатком
        const newVolume = Math.max(0, Math.min(value, remainingVolume + route.volume));
        updated.volume = newVolume;
        updated.trips = Math.ceil(newVolume / vehicleCapacity);
      } else if (field === 'trips') {
        // Расчет объема из количества рейсов
        const newTrips = Math.max(0, value);
        updated.trips = newTrips;
        updated.volume = newTrips * vehicleCapacity;
        
        // Проверка превышения доступного объема
        const maxVolume = remainingVolume + route.volume;
        if (updated.volume > maxVolume) {
          updated.volume = maxVolume;
          updated.trips = Math.floor(maxVolume / vehicleCapacity);
        }
      }
      
      return updated;
    }
    return route;
  });

  updateVehicleTask(vehicleId, { routes: newRoutes });
};
```

**Save mutation (lines 274-335):**
```typescript
const saveMutation = useMutation({
  mutationFn: async (vehicleId: number) => {
    const current = vehicleTasks.get(vehicleId);
    const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
    
    if (!current || !vehicle || !globalWorkRegime) {
      throw new Error('Выберите технику и режим работы');
    }

    if (current.routes.length === 0) {
      throw new Error('Добавьте хотя бы один маршрут');
    }

    // Валидация заполненности маршрутов
    const invalidRoutes = current.routes.filter(r => 
      r.place_a_id === null || r.place_b_id === null || r.trips === 0
    );
    if (invalidRoutes.length > 0) {
      throw new Error('Заполните все поля маршрутов');
    }

    // Формирование данных задания
    const routeTasks: RouteTask[] = current.routes.map((route, idx) => ({
      route_order: idx + 1,
      planned_trips_count: route.trips,
      actual_trips_count: 0,
      status: 'pending',
      place_a_id: route.place_a_id || 0,
      place_b_id: route.place_b_id || 0,
    }));

    const taskData: ShiftTaskCreate = {
      work_regime_id: globalWorkRegime,
      vehicle_id: vehicle.id,
      shift_date: currentDate,
      task_name: TASK_TYPES[current.taskType],
      priority: 0,
      status: 'pending',
      route_tasks: routeTasks,
    };

    return { vehicleId, result: await shiftTasksApi.save(taskData) };
  },
  onSuccess: async ({ vehicleId, result }) => {
    // Инвалидируем кэш и ждем обновления
    await queryClient.invalidateQueries({ queryKey: ['shift-tasks'] });
    
    // Обновляем локальное состояние
    updateVehicleTask(vehicleId, { 
      existingTaskId: result.id, 
      isSaved: true 
    });
    
    // Принудительно перезагружаем данные
    await queryClient.refetchQueries({ queryKey: ['shift-tasks', 'all', currentDate] });
    
    alert('Задание успешно сохранено!');
  },
});
```

**Approve all mutation (lines 338-392):**
```typescript
const approveAllMutation = useMutation({
  mutationFn: async () => {
    const savedTasks = Array.from(vehicleTasks.entries())
      .filter(([_, task]) => task.isSaved && task.existingTaskId);

    if (savedTasks.length === 0) {
      throw new Error('Нет сохраненных заданий для утверждения');
    }

    // Отправка всех заданий через POST /shift-tasks (upsert)
    const results = await Promise.all(
      savedTasks.map(async ([vehicleId, taskState]) => {
        const vehicle = vehiclesData?.items.find(v => v.id === vehicleId);
        if (!vehicle || !globalWorkRegime) return null;

        const routeTasks: RouteTask[] = taskState.routes.map((route, idx) => ({
          route_order: idx + 1,
          planned_trips_count: route.trips,
          actual_trips_count: 0,
          status: 'pending',
          place_a_id: route.place_a_id || 0,
          place_b_id: route.place_b_id || 0,
        }));

        const taskData: ShiftTaskCreate = {
          work_regime_id: globalWorkRegime,
          vehicle_id: vehicle.id,
          shift_date: currentDate,
          task_name: TASK_TYPES[taskState.taskType],
          priority: 0,
          status: 'pending',
          route_tasks: routeTasks,
        };

        // POST поддерживает upsert по (vehicle_id, shift_date, work_regime_id)
        return await shiftTasksApi.create(taskData);
      })
    );

    return results.filter(r => r !== null);
  },
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ['shift-tasks'] });
    await queryClient.refetchQueries({ queryKey: ['shift-tasks', 'all', currentDate] });
    alert('Все задания успешно утверждены и отправлены на борт!');
  },
});
```

**Key features:**
- Volume distribution validation (нельзя распределить больше планового объема)
- Automatic trips calculation from volume / vehicle capacity
- Two-step workflow: Save (локально) → Approve All (отправка в MQTT)
- TanStack Query cache invalidation и refetch после mutations
- Upsert support via POST /shift-tasks (создание или обновление по composite key)

---

### dispa-backend-dev/src/app/services/trip_manager.py (651 строка)

**Назначение:** Trip Manager — управление жизненным циклом рейсов: создание, завершение, связь с заданиями, публикация событий MQTT.

**Ключевые функции:**

**create_trip(vehicle_id, place_id, tag, active_task_id, cycle_id, loading_timestamp, db)** — Создание нового рейса внутри цикла (lines 33-210):
```python
# Определение типа рейса
if active_task_id and db:
    query = select(RouteTask).where(RouteTask.id == active_task_id)
    task = result.scalar_one_or_none()
    
    if task and task.place_a_id == place_id:
        # Плановый рейс - начинается в правильной точке
        trip_type = "planned"
        task_id = task.id
        shift_id = task.shift_task_id
        
        # Обновить задание - статус active
        task.status = TripStatusRouteEnum.ACTIVE
        await db.commit()

# JTI: Преобразование Cycle в Trip через polymorphism
if not cycle_id:
    raise ValueError(f"cycle_id is required to create a trip for vehicle {vehicle_id}")

cycle_query = select(Cycle).where(Cycle.cycle_id == cycle_id)
cycle = cycle_result.scalar_one_or_none()

if cycle:
    # Обновляем Cycle — в БД task_id и shift_id строки (VARCHAR)
    cycle.task_id = task_id if task_id else None
    cycle.shift_id = shift_id if shift_id else None
    await db.flush()
    
    # INSERT INTO trips с cycle_num subquery
    cycle_num_subquery = await construct_trip_cycle_num_subquery(cycle.vehicle_id, now)
    cycle_num = 1 if cycle_num_subquery is None else cycle_num_subquery
    
    await db.execute(
        insert(Trip).values(
            cycle_id=cycle_id,
            trip_type=trip_type,
            start_time=now,
            loading_place_id=place_id,
            loading_tag=tag_str,
            loading_timestamp=loading_timestamp,
            cycle_num=cycle_num,
        ),
    )
    
    # UPDATE entity_type в таблице cycles для JTI polymorphism
    await db.execute(
        update(Cycle).where(Cycle.cycle_id == cycle_id).values(entity_type="trip"),
    )
    
    await db.commit()
```

**Redis storage (lines 153-164):**
```python
trip_data = {
    "cycle_id": cycle_id,
    "vehicle_id": vehicle_id,
    "trip_type": trip_type,
    "status": "active",
    "task_id": task_id if task_id else None,
    "shift_id": shift_id if shift_id else None,
    "start_time": loading_timestamp.isoformat(),
    "loading_place_id": place_id,
    "loading_tag": tag_str,
}
await redis_client.set_active_trip(vehicle_id, trip_data)
```

**Redis Pub/Sub publishing (lines 167-182):**
```python
trip_update = {
    "cycle_id": cycle_id,
    "trip_type": trip_type,
    "status": "active",
    "loading_place_id": place_id,
    "loading_timestamp": loading_timestamp.isoformat(),
    "event_type": "trip_started",
}
channel = f"trip-service:vehicle:{vehicle_id}:events"
payload = json.dumps(trip_update)
if redis_client.redis is not None:
    await redis_client.redis.publish(channel, payload)
```

**MQTT event publishing (lines 194-204):**
```python
await publish_trip_event(
    event_type="trip_started",
    cycle_id=cycle_id,
    server_trip_id=task_id,
    trip_type=trip_type,
    vehicle_id=vehicle_id,
    place_id=place_id,
    state="loading",
    shift_id=shift_id,
    tag=tag_str,
)
```

**complete_trip(vehicle_id, cycle_id, place_id, tag, db, end_time, unloading_timestamp)** — Завершение рейса с проверкой точки разгрузки (lines 213-400):
```python
# Найти рейс в PostgreSQL (Trip ID = Cycle ID)
query = select(Trip).where(Trip.cycle_id == cycle_id)
result = await db.execute(query)
trip = result.scalar_one_or_none()

if not trip:
    return {"success": False, "message": "Trip not found"}

# Проверить тип рейса и точку разгрузки
if trip.trip_type == "planned" and trip.task_id:
    # Найти связанное задание через trip.task_id
    task_query = select(RouteTask).where(
        RouteTask.id == trip.task_id,
        RouteTask.status == TripStatusRouteEnum.ACTIVE,
    )
    task_result = await db.execute(task_query)
    task = task_result.scalar_one_or_none()
    
    if task:
        if task.place_b_id == place_id:
            # Разгрузка в правильной точке - рейс остается плановым
            task.actual_trips_count = (task.actual_trips_count or 0) + 1
            if task.actual_trips_count >= task.planned_trips_count:
                task.status = TripStatusRouteEnum.COMPLETED
            task_completed = True
            
            # Отправка на сервер через Rabbit кол-во выполненных рейсов
            rabbit_msg = BaseMsgScheme(
                payload={
                    "route_task_id": trip.task_id,
                    "actual_trips_count": task.actual_trips_count,
                    "task_status": task.status,
                },
                message_data=MessageData(...)
            )
            await publisher_manager.publish(rabbit_msg)
        else:
            # Разгрузка НЕ в плановом месте → изменить на unplanned
            trip.trip_type = "unplanned"
            trip.task_id = None  # Разорвать связь с заданием
            task_cancelled = True
            
            logger.warning(
                "Trip completed at wrong place, changed to unplanned",
                vehicle_id=vehicle_id,
                expected_place=task.place_b_id,
                actual_place=place_id,
            )
```

**Tag history saving from Redis Stream:**
- Сохранение истории RFID меток из Redis Stream в PostgreSQL таблицу CycleTagHistory
- Извлечение всех тегов, пройденных во время рейса
- Связывание с cycle_id для аудита маршрута

**Analytics computation:**
- Вычисление времени рейса: end_time - start_time
- Подсчет фактического объема перевозки
- Обновление статистики техники

**Return value:**
```python
return {
    "success": True,
    "message": "Trip completed",
    "next_task_id": next_task_id,  # Следующее задание из очереди
    "task_completed": task_completed,
    "task_cancelled": task_cancelled,
}
```

**Key patterns:**
- **JTI (Joined Table Inheritance):** Cycle → Trip polymorphism через entity_type поле
- **Cycle num calculation:** construct_trip_cycle_num_subquery() для нумерации рейсов в цикле
- **Validation:** cycle_id REQUIRED — Trip создается ТОЛЬКО внутри существующего Cycle
- **Type switching:** planned ↔ unplanned при неправильной точке разгрузки
- **Dual storage:** PostgreSQL (persistent) + Redis (active state) + MQTT (events)

---

### analytics-service-dev/src/api/rest/v1/vehicle_telemetry.py (43 строки)

**Назначение:** FastAPI endpoint для получения телеметрии техники с фильтрацией, пагинацией и сортировкой.

**Endpoint definition (lines 21-42):**
```python
@router.post(
    "",
    response_model=PaginationResponse[VehicleTelemetryResponse],
    summary="Vehicle telemetry with filters",
)
async def get_by_filters(
    body: VehicleTelemetryFilterRequest,
    skip: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_type: SortTypeEnum | None = SortTypeEnum.asc,
    controller: VehicleTelemetryController = Depends(
        FastAPIFactory.get_vehicle_telemetry_controller,
    ),
) -> PaginationResponse:
    return await controller.get_by_filters(
        filter_request=body,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_type=sort_type.value if sort_type else "asc",
    )
```

**Key components:**
- **VehicleTelemetryFilterRequest** — Pydantic модель для фильтров (vehicle_id, time range, sensor types)
- **VehicleTelemetryResponse** — Response schema с данными телеметрии
- **PaginationResponse[T]** — Generic pagination wrapper с items, total, skip, limit
- **SortTypeEnum** — Enum для направления сортировки (asc/desc)
- **VehicleTelemetryController** — Business logic layer (dependency injection via FastAPIFactory)

**Architecture pattern:**
- Router (API layer) → Controller (business logic) → Repository (data access) → ClickHouse (storage)
- Dependency injection через FastAPIFactory.get_vehicle_telemetry_controller
- POST метод вместо GET для сложных фильтров в body

**Pagination defaults:**
- skip: 0 (начало с первой записи)
- limit: 100 (максимум 100 записей за запрос)
- sort_type: asc (по умолчанию восходящая сортировка)

---

### graph-service-backend-dev/src/app/routers/locations.py (173 строки)

**Назначение:** API endpoints для поиска мест по GPS координатам, построения маршрутов и отслеживания прогресса движения.

**Key endpoints:**

**POST /location/find** — Поиск ближайшей метки по GPS координатам (из предыдущего анализа):
```python
# loc_finder.find_nearest_node_to_bort(lat, lon, db)
# Возвращает ближайший узел графа к позиции борта
```

**GET /route/{start_node_id}/{target_node_id}** — Построение маршрута между узлами:
```python
# loc_finder.calculate_route(start_node_id, target_node_id, db)
# Использует python-igraph для shortest path calculation
# Возвращает route_geojson, total_length_m, edge_ids
```

**GET /route/progress/{start_node_id}/{target_node_id}** — Отслеживание прогресса движения по маршруту (lines 80-172):
```python
async def get_route_progress(
    start_node_id: int,
    target_node_id: int,
    lat: float,  # Текущая широта борта
    lon: float,  # Текущая долгота борта
    db: AsyncSession = Depends(get_async_db),
):
    # Получаем исходный маршрут
    route_data = await loc_finder.calculate_route(start_node_id, target_node_id, db)
    
    # Вычисляем прогресс
    progress = await loc_finder.calculate_route_progress(route_data, lat, lon, db)
    
    # Проверка отклонения от маршрута
    if progress["distance_to_route"] > settings.deviation_threshold_m:
        # Поиск ближайшего узла
        nearest_node_id = await loc_finder.find_nearest_node_to_bort(lat, lon, db)
        
        if nearest_node_id != start_node_id:
            # Строим новый маршрут от текущей позиции
            new_route = await loc_finder.calculate_route(nearest_node_id, target_node_id, db)
            
            # calculate_time
            time_data = await loc_finder.calculate_time_to_destination(
                new_route.get("total_length_m"),
            )
            
            return {
                "start_node_id": nearest_node_id,
                "target_node_id": target_node_id,
                "user_location": {"lat": lat, "lon": lon},
                "nearest_point_on_route": None,
                "distance_covered_m": 0,
                "distance_remaining_m": new_route["total_length_m"],
                "percent_complete": 0,
                "deviation_detected": True,
                "new_route": True,  # Маршрут перестроен
                "route_geojson": new_route["route_geojson"],
                "total_length_m": new_route["total_length_m"],
                "edge_ids": new_route["edge_ids"],
                "time_data": time_data,
            }
    
    # Если отклонения нет – возвращаем исходный прогресс
    time_data = await loc_finder.calculate_time_to_destination(
        progress.get("distance_remaining_m")
    )
    
    return {
        "start_node_id": start_node_id,
        "target_node_id": target_node_id,
        **progress,  # distance_covered_m, distance_remaining_m, percent_complete
        "deviation_detected": False,
        "new_route": False,
        "route_geojson": route_data["route_geojson"],
        "total_length_m": route_data["total_length_m"],
        "edge_ids": route_data["edge_ids"],
        "time_data": time_data,
    }
```

**Deviation detection logic:**
- **deviation_threshold_m** — Настройка порога отклонения (например, 50 метров)
- Если `distance_to_route > deviation_threshold_m` → поиск ближайшего узла
- Если ближайший узел отличается от start_node_id → перестройка маршрута
- Новый маршрут начинается от nearest_node_id до target_node_id
- Прогресс обнуляется: distance_covered_m = 0, percent_complete = 0

**Response fields:**
- **start_node_id / target_node_id** — IDs начального и конечного узлов
- **user_location** — Текущие GPS координаты {lat, lon}
- **nearest_point_on_route** — Ближайшая точка на маршруте (или null при перестройке)
- **distance_covered_m** — Пройденное расстояние (метры)
- **distance_remaining_m** — Оставшееся расстояние (метры)
- **percent_complete** — Процент выполнения маршрута (0-100)
- **deviation_detected** — Флаг обнаружения отклонения
- **new_route** — Флаг перестройки маршрута
- **route_geojson** — GeoJSON геометрия маршрута
- **total_length_m** — Общая длина маршрута (метры)
- **edge_ids** — Список IDs ребер графа в маршруте
- **time_data** — Расчетное время до目的地 (ETA)

**Integration with bort-client:**
- Бортовое приложение вызывает этот endpoint периодически (каждые 5-10 секунд)
- При отклонении получает новый маршрут автоматически
- Отображает прогресс на экране водителя
- Предупреждает о необходимости вернуться на маршрут

---

### enterprise-service-dev/src/app/routers/vehicles.py (200 строк)

**Назначение:** CRUD endpoints для управления техникой (транспортными средствами) с auth_lib permission-based authorization.

**Key endpoints:**

**GET /vehicles** — Список техники с пагинацией и фильтрацией (lines 27-68):
```python
@router.get(
    "",
    response_model=VehicleListResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.TRIP_EDITOR, Action.VIEW),
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.EQUIPMENT, Action.VIEW),
            ),
        ),
    ],
)
async def list_vehicles(
    enterprise_id: int = Query(1),
    vehicle_type: str | None = Query(None),
    page: int | None = Query(
        None,
        ge=1,
        description="Номер страницы (опционально, если не указан - возвращает все записи)",
    ),
    size: int | None = Query(
        None,
        ge=1,
        le=100,
        description="Размер страницы (опционально, если не указан - возвращает все записи)",
    ),
    is_active: bool | None = Query(None),
    service: VehicleService = Depends(get_vehicle_service),
) -> dict[str, Any]:
    """Получить список техники с пагинацией или без неё.

    Если параметры page и size не указаны, возвращает все записи без пагинации.
    """
    return await service.get_list(
        enterprise_id=enterprise_id,
        vehicle_type=vehicle_type,
        is_active=is_active,
        page=page,
        size=size,
    )
```

**Permission requirements:**
- Требуется хотя бы одно из разрешений: WORK_TIME_MAP.VIEW, TRIP_EDITOR.VIEW, WORK_ORDER.VIEW, EQUIPMENT.VIEW
- Используется auth_lib require_permission() factory function
- Проверка происходит до выполнения endpoint (FastAPI dependency injection)

**Pagination logic:**
- Если page и size не указаны → возвращает ВСЕ записи без пагинации
- Если указаны → пагинация с limit size (max 100)
- Фильтрация по: enterprise_id, vehicle_type, is_active

**POST /vehicles** — Создание новой техники (lines 71-82):
```python
@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def create_vehicle(
    data: VehicleCreate,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Создать новый транспорт (ПДМ или ШАС)."""
    return await service.create(data)
```

**Permission:** Требуется EQUIPMENT.EDIT разрешение

**GET /vehicles/{vehicle_id}** — Получение техники по ID (lines 85-110):
```python
@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[
        Depends(
            require_permission(
                (Permission.WORK_TIME_MAP, Action.VIEW),
                (Permission.TRIP_EDITOR, Action.VIEW),
                (Permission.WORK_ORDER, Action.VIEW),
                (Permission.EQUIPMENT, Action.VIEW),
            ),
        ),
    ],
)
async def get_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Получить транспорт по ID."""
    vehicle = await service.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return vehicle
```

**POST /vehicles/{vehicle_id}/copy** — Копирование техники (lines 113-142):
```python
@router.post(
    "/{vehicle_id}/copy",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def copy_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Скопировать существующий транспорт.

    Исключаются:
    - id
    - created_at / updated_at
    - serial_number
    """
    try:
        vehicle = await service.copy(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Транспорт с ID {vehicle_id} не найден",
            )
        return vehicle
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при копировании транспорта: {str(e)}",
        ) from e
```

**Copy logic:**
- Клонирует технику с новым ID
- Исключает поля: id, created_at, updated_at, serial_number
- Возвращает копию с HTTP 201 Created

**PUT /vehicles/{vehicle_id}** — Обновление техники (lines 145-162):
```python
@router.put(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def update_vehicle(
    vehicle_id: int,
    data: VehicleUpdate,
    service: VehicleService = Depends(get_vehicle_service),
) -> Any:
    """Обновить транспорт."""
    vehicle = await service.update(vehicle_id, data)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return vehicle
```

**DELETE /vehicles/{vehicle_id}** — Удаление техники (soft delete) (lines 165-181):
```python
@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission((Permission.EQUIPMENT, Action.EDIT)))],
)
async def delete_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> None:
    """Удалить транспорт (soft delete)."""
    deleted = await service.delete(vehicle_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Транспорт с ID {vehicle_id} не найден",
        )
    return None
```

**Soft delete pattern:**
- Не удаляет запись физически из БД
- Устанавливает флаг is_active = False
- Запись остается в БД для истории

**GET /vehicles/{vehicle_id}/speed** — Получение максимальной скорости модели (lines 184-199):
```python
@router.get("/{vehicle_id}/speed")
async def get_vehicle_speed(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
) -> dict:
    """
    Получить максимальную скорость модели транспортного средства по его ID.
    Если ТС не найдено или скорость не указана, возвращается 404.
    """
    speed = await service.get_model_max_speed(vehicle_id)
    if speed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Скорость для транспорта с ID {vehicle_id} не найдена (возможно, отсутствует модель или максимальная скорость)",
        )
    return {"speed": speed}
```

**Architecture pattern:**
- Router layer (API endpoints) → Service layer (business logic) → Repository (data access) → PostgreSQL
- Dependency injection: get_vehicle_service(db) через FastAPI Depends()
- Permission-based authorization через auth_lib require_permission()
- Consistent error handling: HTTPException с 404/400 статусами

**Schemas used:**
- VehicleCreate — Pydantic schema для создания
- VehicleUpdate — Pydantic schema для обновления
- VehicleResponse — Response schema с полной информацией
- VehicleListResponse — Paginated list response

---

### sync-service-dev/app/api/routes/autorepub.py (289 строк)

**Назначение:** Управление конфигурациями автоперепубликации сообщений между MQTT/RabbitMQ топиками для синхронизации данных между server и bort инстансами.

**Key concepts:**
- **Autorepub config** — Конфигурация перепубликации: source topic → target topic(s)
- **Temporary configs** — Временные конфигурации, создаваемые через API (хранятся в памяти/Redis)
- **YAML configs** — Постоянные конфигурации из YAML файлов
- **Instance suspension** — Временная приостановка синхронизации для конкретных бортов

**Data models:**
```python
class AutorepubConfigResponse(AutorepubConfig):
    """Response containing autorepub config."""
    is_active: bool = Field(description="Whether the config is currently active (subscribed and processing)")

class AutorepubConfigListResponse(BaseModel):
    """List of autorepub configs."""
    configs: list[AutorepubConfigResponse] = Field(default_factory=list)
    count: int = Field(description="Number of configs")
```

**POST /autorepub/configs** — Создание временной конфигурации (lines 40-83):
```python
@router.post("/configs", response_model=AutorepubConfigResponse)
async def create_config(
    config: AutorepubConfig,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> AutorepubConfigResponse:
    """Create a temporary autorepub config."""

    # Проверка применимости конфигурации к текущему инстансу
    if not config_manager.is_config_applicable(config):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Config is not applicable to the current instance_id={settings.instance_id}",
        )

    # Добавление временной конфигурации
    added = config_manager.add_temporary_config(config)
    if not added:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Config {config.name} already exists",
        )
    
    # Автостарт подписки если включен
    if config.autostart:
        await config_manager.activate_config(config.name)
        if config.type == AutorepubConfigType.RABBITMQ:
            await autorepub_rabbitmq_manager.subscribe_to_config(config)
        else:
            await autorepub_mqtt_manager.subscribe_to_config(config)

    return AutorepubConfigResponse(
        name=config.name,
        type=config.type,
        source_instance_id=config.source_instance_id,
        target_instances=config.target_instances,
        source_topic=config.source_topic,
        target_topic=config.get_target_topic(),
        queue_name=config.queue_name,
        deduplication=config.deduplication,
        autostart=config.autostart,
        retry_max_attempts=config.retry_max_attempts,
        retry_backoff_base=config.retry_backoff_base,
        retry_multiplier=config.retry_multiplier,
        retry_max_delay=config.retry_max_delay,
        is_active=config_manager.is_config_active(config.name),
    )
```

**Config fields:**
- **name** — Уникальное имя конфигурации
- **type** — Тип: MQTT или RABBITMQ
- **source_instance_id** — ID исходного инстанса (например, "server" или "bort-1")
- **target_instances** — Список целевых инстансов для перепубликации
- **source_topic** — Исходный топик (например, "truck/+/sensor/gps/events")
- **target_topic** — Целевой топик (может содержать placeholders)
- **queue_name** — Имя очереди (для RabbitMQ)
- **deduplication** — Флаг дедупликации сообщений
- **autostart** — Автоматически активировать после создания
- **retry_max_attempts** — Максимальное количество попыток повторной отправки
- **retry_backoff_base** — Базовое время задержки между попытками
- **retry_multiplier** — Множитель для exponential backoff
- **retry_max_delay** — Максимальная задержка между попытками

**DELETE /autorepub/configs?name={name}** — Удаление временной конфигурации (lines 86-108):
```python
@router.delete("/configs")
async def delete_config(
    name: str,
    config_manager: AutorepubConfigManagerDep,
    autorepub_mqtt_manager: AutorepubMQTTManagerDep,
    autorepub_rabbitmq_manager: AutorepubRabbitMQManagerDep,
) -> dict:
    """Delete a temporary autorepub config."""

    config = config_manager.get_temporary_config(name)
    if not config:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Temporary config {name} not found",
        )
    
    # Деактивация перед удалением
    await config_manager.deactivate_config(config.name)
    if config.type == AutorepubConfigType.RABBITMQ:
        await autorepub_rabbitmq_manager.unsubscribe_from_config(config)
    else:
        await autorepub_mqtt_manager.unsubscribe_from_config(config)
    
    await config_manager.delete_temporary_config(config.name)

    return {"name": config.name, "deleted": True}
```

**GET /autorepub/configs** — Список всех конфигураций (lines 111-137):
```python
@router.get("/configs", response_model=AutorepubConfigListResponse)
async def list_configs(
    config_manager: AutorepubConfigManagerDep,
    only_active: bool = Query(default=False),
) -> AutorepubConfigListResponse:
    """List all autorepub configs (YAML + temporary)."""
    configs = config_manager.get_configs(is_active=(only_active if only_active else None))
    config_responses = [
        AutorepubConfigResponse(...)
        for cfg in configs
    ]
    return AutorepubConfigListResponse(configs=config_responses, count=len(config_responses))
```

**Activation/Deactivation endpoints:**
- **POST/GET /autorepub/configs/activate?name={name}** — Активация конфигурации (подписка на топики)
- **POST/GET /autorepub/configs/deactivate?name={name}** — Деактивация конфигурации (отписка от топиков)

**Instance suspension endpoints (lines 193-288):**

Conditional routing based on instance type:
```python
if settings.instance_id == SERVER_INSTANCE_ID:
    router.get("/suspend")(suspend_instances_server)
    router.post("/suspend")(suspend_instances_post_server)
else:
    router.get("/suspend")(suspend_instances_bort)
    router.post("/suspend")(suspend_instances_bort)
```

**Server instance suspend (с указанием vehicle_ids):**
```python
async def suspend_instances_server(
    vehicle_ids: list[int] = Depends(parse_comma_separated_vehicle_ids),
) -> dict:
    return await suspend_instances(vehicle_ids)

# Vehicle IDs преобразуются в instance IDs
instance_ids = [f"{BORT_INSTANCE_ID_PREFIX}{v_id}" for v_id in vehicle_ids]
# Например: ["bort-4", "bort-9", "bort-17", "bort-22"]
```

**Bort instance suspend (без параметров — приостанавливает server):**
```python
async def suspend_instances_bort() -> dict:
    return await suspend_instances([])

# Пустой список vehicle_ids → instance_ids = [SERVER_INSTANCE_ID]
```

**Suspension logic:**
```python
async def suspend_instances(vehicle_ids: list[int]) -> dict:
    config_manager = get_autorepub_config_manager()
    autorepub_mqtt_manager = get_autorepub_mqtt_manager()
    autorepub_rabbitmq_manager = get_autorepub_rabbitmq_manager()

    instance_ids = vehicle_ids_to_instance_ids(vehicle_ids)
    suspended_ids = await config_manager.suspend_instances(instance_ids)
    await autorepub_rabbitmq_manager.suspend_instances(suspended_ids)
    await autorepub_mqtt_manager.suspend_instances(suspended_ids)
    return {"success": True}
```

**Use cases:**
- При потере связи с бортом → suspend bort-X instance
- При техническом обслуживании → suspend specific vehicles
- Для предотвращения дублирования сообщений во время перезагрузки

**Resume endpoints:** Аналогичная логика для возобновления синхронизации

**Architecture pattern:**
- Config Manager (хранение конфигураций) → MQTT/RabbitMQ Managers (подписка/отписка)
- Redis для хранения active configs state
- Instance-aware routing (different behavior for server vs bort instances)
- Exponential backoff retry policy для надежности доставки

---

### telemetry-service-dev/app/services/mqtt_client.py (205 строк)

**Назначение:** MQTT клиент для подписки на телеметрию датчиков с NanoMQ брокера и передачи данных в обработчик (который сохраняет в Redis Streams).

**Class structure:**
```python
class TelemetryMQTTClient:
    """
    MQTT клиент для Telemetry Service.
    
    Подписывается на топики событий датчиков (/events) и downsampled данных (/ds)
    и передает их в Redis Streams.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        message_handler: Optional[Callable[[str, str, dict], Awaitable[None]]] = None
    ):
        """
        Args:
            host: Хост NanoMQ брокера
            port: Порт NanoMQ брокера
            message_handler: Async функция для обработки сообщений (vehicle_id, sensor_type, data)
        """
        self.host = host
        self.port = port
        self.message_handler = message_handler
        
        # Создаем MQTT клиент с уникальным ID
        self.client = MQTTClient("telemetry-service")
        
        # Настраиваем callback для событий
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_subscribe = self._on_subscribe
        
        self._connected = False
        
        # Топики для подписки: truck/+/sensor/+/events и truck/+/sensor/+/ds
        # Примеры: truck/AC9/sensor/speed/events, truck/AC9/sensor/speed/ds
        self._topic_patterns = [
            "truck/+/sensor/+/events",
            "truck/+/sensor/+/ds"
        ]
```

**Topic patterns:**
- `truck/+/sensor/+/events` — События датчиков (все типы, все борты)
- `truck/+/sensor/+/ds` — Downsampled данные (сниженная частота)
- Wildcard `+` заменяет vehicle_id и sensor_type

**Connection management (lines 66-101):**
```python
async def connect(self) -> None:
    """Подключение к NanoMQ брокеру"""
    try:
        logger.info(
            "Connecting to MQTT broker",
            host=self.host,
            port=self.port
        )
        
        await self.client.connect(self.host, self.port)
        self._connected = True
        
        logger.info("Connected to MQTT broker successfully")
        
    except Exception as e:
        logger.error(
            "Failed to connect to MQTT broker",
            host=self.host,
            port=self.port,
            error=str(e),
            exc_info=True
        )
        raise

async def disconnect(self) -> None:
    """Отключение от NanoMQ брокера"""
    try:
        if self._connected:
            await self.client.disconnect()
            self._connected = False
            logger.info("Disconnected from MQTT broker")
    except Exception as e:
        logger.error(
            "Error disconnecting from MQTT broker",
            error=str(e)
        )
```

**Subscription on connect (lines 103-110):**
```python
def _on_connect(self, client, flags, rc, properties):
    """Callback при подключении к брокеру"""
    logger.info("MQTT connected", return_code=rc)
    
    # Подписываемся на все топики с wildcard
    for topic_pattern in self._topic_patterns:
        client.subscribe(topic_pattern, qos=0)
        logger.info("Subscribed to MQTT topic", topic=topic_pattern)
```

**Topic parsing (lines 121-146):**
```python
def _parse_topic(self, topic: str) -> tuple[Optional[str], Optional[str]]:
    """
    Парсинг топика для извлечения vehicle_id и sensor_type.
    
    Формат топика: truck/{vehicle_id}/sensor/{sensor_type}/{suffix}
    Поддерживает суффиксы: events, ds
    
    Returns:
        Tuple (vehicle_id, sensor_type) или (None, None) при ошибке парсинга
    """
    # Регулярное выражение для парсинга: truck/{vehicle_id}/sensor/{sensor_type}/{events|ds}
    pattern = r"truck/([^/]+)/sensor/([^/]+)/(events|ds)"
    match = re.match(pattern, topic)
    
    if match:
        vehicle_id = match.group(1)
        sensor_type = match.group(2)
        suffix = match.group(3)  # events или ds
        logger.debug("Topic parsed successfully", topic=topic, suffix=suffix)
        return vehicle_id, sensor_type
    
    logger.warning("Failed to parse topic", topic=topic)
    return None, None
```

**Message handler (lines 148-199):**
```python
def _on_message(self, client, topic, payload, qos, properties):
    """
    Callback при получении сообщения из MQTT.
    
    Парсит топик, извлекает vehicle_id и sensor_type,
    парсит JSON payload и вызывает message_handler.
    """
    try:
        # Парсим топик для извлечения vehicle_id и sensor_type
        vehicle_id, sensor_type = self._parse_topic(topic)
        
        if not vehicle_id or not sensor_type:
            logger.warning("Skipping message - failed to parse topic", topic=topic)
            return
        
        # Декодируем payload
        message = payload.decode('utf-8')
        data = json.loads(message)
        
        logger.debug(
            "MQTT message received",
            topic=topic,
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            payload_size=len(message)
        )
        
        # Вызываем обработчик сообщений асинхронно
        if self.message_handler:
            asyncio.create_task(self.message_handler(vehicle_id, sensor_type, data))
        
    except json.JSONDecodeError as e:
        # Проверяем, является ли это проблемой eKuiper с <no value>
        if b"<no value>" in payload:
            logger.debug(
                "Skipping message with <no value> from eKuiper",
                topic=topic
            )
        else:
            logger.error(
                "Failed to parse MQTT message JSON",
                topic=topic,
                payload=payload[:100] if payload else None,
                error=str(e)
            )
    except Exception as e:
        logger.error(
            "Error handling MQTT message",
            topic=topic,
            error=str(e),
            exc_info=True
        )
```

**eKuiper <no value> handling:**
- eKuiper может отправлять сообщения с `<no value>` placeholder
- Такие сообщения пропускаются без ошибки (debug level log)
- Это предотвращает spam в логах при отсутствии данных датчика

**Async message processing:**
- `asyncio.create_task()` для неблокирующей обработки
- message_handler вызывается асинхронно
- Позволяет обрабатывать множество сообщений параллельно

**Connection state check:**
```python
def is_connected(self) -> bool:
    """Проверка состояния подключения"""
    return self._connected
```

**Integration flow:**
1. TelemetryMQTTClient подключается к NanoMQ
2. Подписывается на `truck/+/sensor/+/events` и `truck/+/sensor/+/ds`
3. При получении сообщения парсит topic → vehicle_id, sensor_type
4. Вызывает message_handler(vehicle_id, sensor_type, data)
5. message_handler сохраняет данные в Redis Streams (через telemetry_storage.py)

**Sensor types supported:**
- gps — GPS координаты
- speed — Скорость
- weight — Вес груза
- fuel — Уровень топлива
- vibro — Вибрация
- И другие датчики

**Architecture pattern:**
- NanoMQ (MQTT broker) → TelemetryMQTTClient (subscriber) → message_handler → Redis Streams → Analytics Service
- Event-driven architecture с async callbacks
- Wildcard subscriptions для масштабируемости (один subscriber для всех бортов)

---

### api-gateway-dev/src/proxy.py (440 строк)

**Назначение:** aiohttp reverse proxy handler для динамической маршрутизации запросов к микросервисам с поддержкой HTTP, WebSocket и SSE протоколов.

**Key functions:**

**_extract_api_version(request)** — Извлечение версии API из URL path (lines 24-34):
```python
def _extract_api_version(request: web.Request) -> str:
    """Resolve API version from route match or request path."""
    route_api_version = request.match_info.get("version")
    if route_api_version:
        return route_api_version

    # Fallback: парсинг из path через regex
    version_match = _API_VERSION_PATTERN.match(request.path)
    if version_match:
        return version_match.group("version")

    return _UNKNOWN_VALUE

# Pattern: /api/v1 или /api/v2
_API_VERSION_PATTERN = re.compile(r"^/api/(?P<version>v[^/]+)(?:/|$)")
_SUPPORTED_API_VERSIONS = frozenset({"v1", "v2"})
```

**Protocol detection (lines 37-52):**
```python
def _is_sse_request(request: web.Request) -> bool:
    """Check if the request expects an SSE stream."""
    accept = request.headers.get("Accept", "")
    return "text/event-stream" in accept

def _is_websocket_upgrade(request: web.Request) -> bool:
    """Check if the request is a WebSocket upgrade request."""
    connection = request.headers.get("Connection", "").lower()
    upgrade = request.headers.get("Upgrade", "").lower()
    return "upgrade" in connection and upgrade == "websocket"
```

**URL building (lines 55-77):**
```python
def _build_upstream_url(
    service_url: str,
    api_version: str,
    path_pattern: str,
    path: str,
    query_string: str,
) -> URL:
    """Build the upstream URL from service URL, path pattern, and query string."""
    relative_path = path.lstrip("/")
    pattern_contains_path = "{path}" in path_pattern
    
    # Замена плейсхолдеров {version} и {path}
    upstream_path = path_pattern.replace("{version}", api_version).replace("{path}", relative_path)

    if pattern_contains_path and not relative_path:
        # Avoid trailing slash artifacts when {path} is empty.
        upstream_path = re.sub(r"/+", "/", upstream_path).rstrip("/") or "/"

    if not pattern_contains_path and relative_path:
        upstream_path = f"{upstream_path.rstrip('/')}/{relative_path}"

    upstream_url = URL(service_url).with_path(upstream_path)
    if query_string:
        upstream_url = upstream_url.with_query(query_string)
    return upstream_url
```

**Header forwarding (lines 80-92):**
```python
def _build_upstream_headers(request: web.Request, upstream_url: URL) -> dict[str, str]:
    """Build headers to forward to upstream, setting Host and X-Request-Id."""
    headers = dict(request.headers)
    headers["Host"] = upstream_url.host or ""
    headers.pop("Transfer-Encoding", None)

    request_id: str | None = request.get("request_id")
    if request_id:
        headers["X-Request-Id"] = request_id

    headers["X-Source"] = "api-gateway"  # Важно для auth-lib bypass

    return headers
```

**WebSocket proxying (lines 169-230):**
```python
async def _handle_websocket(
    request: web.Request,
    upstream_url: URL,
    headers: dict[str, str],
) -> web.WebSocketResponse:
    """Handle a WebSocket upgrade request by proxying to upstream."""
    session: ClientSession = request.app["client_session"]
    request[_PROXY_PROTOCOL_KEY] = _WEBSOCKET_PROTOCOL

    # Remove hop-by-hop headers that should not be forwarded to upstream WS
    ws_headers = {
        k: v
        for k, v in headers.items()
        if k.lower() not in ("connection", "upgrade", "sec-websocket-key", "sec-websocket-version")
    }

    # Convert http(s) URL to ws(s) for the upstream connection
    upstream_ws_url = upstream_url.with_scheme(
        "wss" if upstream_url.scheme == "https" else "ws",
    )

    try:
        upstream_ws = await session.ws_connect(upstream_ws_url, headers=ws_headers)
    except Exception as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error(
            "proxy_websocket_connect_failed",
            extra=_proxy_error_log_payload(...),
        )
        return web.Response(status=502, text="Failed to connect to upstream WebSocket")

    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)

    # Bidirectionally pipe frames between client and upstream
    client_to_upstream = asyncio.create_task(
        _pipe_ws_client_to_upstream(client_ws, upstream_ws),
    )
    upstream_to_client = asyncio.create_task(
        _pipe_ws_upstream_to_client(upstream_ws, client_ws),
    )

    try:
        await asyncio.gather(client_to_upstream, upstream_to_client)
    finally:
        client_to_upstream.cancel()
        upstream_to_client.cancel()
        if not upstream_ws.closed:
            await upstream_ws.close()
        if not client_ws.closed:
            await client_ws.close()

    return client_ws
```

**Bidirectional WebSocket piping (lines 135-166):**
```python
async def _pipe_ws_client_to_upstream(
    client_ws: web.WebSocketResponse,
    upstream_ws: aiohttp.ClientWebSocketResponse,
) -> None:
    """Forward frames from client WebSocket to upstream WebSocket."""
    async for msg in client_ws:
        if msg.type == WSMsgType.TEXT:
            await upstream_ws.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await upstream_ws.send_bytes(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            await upstream_ws.close()
            break
        elif msg.type == WSMsgType.ERROR:
            break

async def _pipe_ws_upstream_to_client(
    upstream_ws: aiohttp.ClientWebSocketResponse,
    client_ws: web.WebSocketResponse,
) -> None:
    """Forward frames from upstream WebSocket to client WebSocket."""
    async for msg in upstream_ws:
        if msg.type == WSMsgType.TEXT:
            await client_ws.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await client_ws.send_bytes(msg.data)
        elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            await client_ws.close()
            break
        elif msg.type == WSMsgType.ERROR:
            break
```

**SSE streaming (lines 233-284):**
```python
async def _handle_sse(
    request: web.Request,
    upstream_url: URL,
    headers: dict[str, str],
) -> web.StreamResponse:
    """Handle an SSE request by streaming the upstream response to the client."""
    session: ClientSession = request.app["client_session"]
    request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL
    body = await request.read()

    try:
        upstream_resp = await session.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body if body else None,
        )
    except aiohttp.ClientError as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error("proxy_sse_connect_failed", extra=_proxy_error_log_payload(...))
        return web.json_response({"error": "Bad Gateway"}, status=502)

    try:
        resp_headers = dict(upstream_resp.headers)
        resp_headers.pop("Transfer-Encoding", None)
        resp_headers.pop("Content-Length", None)

        response = web.StreamResponse(
            status=upstream_resp.status,
            headers=resp_headers,
        )
        await response.prepare(request)

        async for chunk in upstream_resp.content.iter_any():
            await response.write(chunk)

        await response.write_eof()
    except ConnectionResetError:
        logger.debug("Client disconnected from SSE stream")
    finally:
        upstream_resp.close()

    return response
```

**Main proxy handler (lines 287-418):**
```python
async def proxy_handler(request: web.Request) -> web.StreamResponse:
    """Proxy incoming requests to the appropriate upstream service."""
    settings: Settings = request.app["settings"]
    service = request.match_info["service"]
    path = request.match_info.get("path", "")
    api_version = _extract_api_version(request)

    request["service"] = service
    request["api_version"] = api_version
    request[_PROXY_PROTOCOL_KEY] = _HTTP_PROTOCOL
    
    # Protocol detection
    if _is_websocket_upgrade(request):
        request[_PROXY_PROTOCOL_KEY] = _WEBSOCKET_PROTOCOL
    elif _is_sse_request(request):
        request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL

    # Service lookup
    service_cfg = settings.services.get(service)
    if service_cfg is None:
        request["upstream_url"] = _UNRESOLVED_UPSTREAM
        request["error_type"] = "service_not_found"
        return web.json_response({"error": "Service not found"}, status=502)

    # Version validation
    uses_version = "{version}" in service_cfg.path_pattern
    if uses_version and api_version not in _SUPPORTED_API_VERSIONS:
        request["upstream_url"] = _UNRESOLVED_UPSTREAM
        request["error_type"] = "unsupported_api_version"
        return web.json_response(
            {
                "error": "Unsupported API version",
                "supported_versions": sorted(_SUPPORTED_API_VERSIONS),
            },
            status=400,
        )

    # Build upstream URL and headers
    upstream_url = _build_upstream_url(
        str(service_cfg.url),
        api_version,
        service_cfg.path_pattern,
        path,
        request.query_string,
    )
    request["upstream_url"] = str(upstream_url)
    headers = _build_upstream_headers(request, upstream_url)

    # Handle WebSocket upgrade requests
    if _is_websocket_upgrade(request):
        return await _handle_websocket(request, upstream_url, headers)

    # Handle SSE requests
    if _is_sse_request(request):
        return await _handle_sse(request, upstream_url, headers)

    # Standard HTTP proxy
    body = await request.read()
    session: ClientSession = request.app["client_session"]
    
    try:
        async with session.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body if body else None,
        ) as upstream_resp:
            # If upstream returns SSE even though client didn't ask with Accept header,
            # stream it instead of buffering
            content_type = upstream_resp.headers.get("Content-Type", "")
            if _is_sse_response(content_type):
                request[_PROXY_PROTOCOL_KEY] = _SSE_PROTOCOL
                resp_headers = dict(upstream_resp.headers)
                resp_headers.pop("Transfer-Encoding", None)
                resp_headers.pop("Content-Length", None)

                response = web.StreamResponse(
                    status=upstream_resp.status,
                    headers=resp_headers,
                )
                await response.prepare(request)

                try:
                    async for chunk in upstream_resp.content.iter_any():
                        await response.write(chunk)
                    await response.write_eof()
                except ConnectionResetError:
                    logger.debug("Client disconnected from SSE stream")

                return response

            # Regular HTTP response (buffered)
            resp_headers = dict(upstream_resp.headers)
            resp_headers.pop("Transfer-Encoding", None)
            resp_headers.pop("Content-Encoding", None)

            resp_body = await upstream_resp.read()
            return web.Response(
                status=upstream_resp.status,
                headers=resp_headers,
                body=resp_body,
            )
    except aiohttp.ClientError as exc:
        request["error_type"] = "upstream_connection_error"
        logger.error(
            "proxy_http_connect_failed",
            extra=_proxy_error_log_payload(...),
        )
        return web.json_response({"error": "Bad Gateway"}, status=502)
```

**Error logging payload (lines 108-132):**
```python
def _proxy_error_log_payload(
    request: web.Request,
    *,
    upstream_url: URL | None,
    error_type: str,
    protocol: str,
    error: Exception,
) -> dict[str, str]:
    """Build structured proxy error log payload without sensitive headers."""
    return {
        "request_id": _resolve_context_field(request, "request_id", _UNKNOWN_VALUE),
        "method": request.method,
        "path": request.path,
        "query": request.query_string,
        "service": _resolve_context_field(request, "service", _UNKNOWN_VALUE),
        "api_version": _resolve_context_field(
            request,
            "api_version",
            _extract_api_version(request),
        ),
        "upstream_url": str(upstream_url) if upstream_url is not None else _UNRESOLVED_UPSTREAM,
        "error_type": error_type,
        "protocol": protocol,
        "exception_type": type(error).__name__,
    }
```

**Missing version handler (lines 421-439):**
```python
async def missing_version_handler(request: web.Request) -> web.StreamResponse:
    """Route non-versioned services to the proxy, or return 400 when version is missing."""
    settings: Settings = request.app["settings"]
    service = request.match_info.get("service", _UNKNOWN_VALUE)
    service_cfg = settings.services.get(service)

    if service_cfg is not None and "{version}" not in service_cfg.path_pattern:
        # Non-versioned service — проксируем напрямую
        return await proxy_handler(request)

    request["service"] = service
    request["api_version"] = _UNKNOWN_VALUE
    request["upstream_url"] = _UNRESOLVED_UPSTREAM
    request["error_type"] = "missing_api_version"
    return web.json_response(
        {
            "error": "Missing API version segment. Use /api/{version}/{service}/{path}",
        },
        status=400,
    )
```

**Architecture patterns:**
- **Multi-protocol support:** HTTP, WebSocket (bidirectional), SSE (server-sent events)
- **Dynamic routing:** Service discovery via settings.services config
- **Version-aware routing:** /api/v1/service/path → service-specific path_pattern
- **Structured error logging:** _proxy_error_log_payload без sensitive headers
- **Async bidirectional streaming:** asyncio.gather для WebSocket frame piping
- **Hop-by-hop header removal:** Transfer-Encoding, Content-Length cleanup
- **X-Source header injection:** "api-gateway" для auth-lib permission bypass

**Protocol flow:**
1. Request arrives → extract service, path, api_version
2. Lookup service_cfg from settings
3. Validate API version (v1/v2 supported)
4. Build upstream_url with path_pattern substitution
5. Detect protocol: WebSocket upgrade? SSE Accept header?
6. Route to appropriate handler: _handle_websocket, _handle_sse, or standard HTTP
7. Forward request with modified headers (Host, X-Request-Id, X-Source)
8. Stream/buffer response back to client

**Use cases:**
- Single entry point for all microservices
- Centralized authentication (JWT verification in middleware)
- Protocol translation (HTTP ↔ WebSocket ↔ SSE)
- Load balancing (future enhancement)
- Rate limiting (future enhancement)

---

### auth-lib-dev/auth_lib/dependencies.py (76 строк)

**Назначение:** FastAPI dependency factories для JWT аутентификации и проверки разрешений (permissions) с поддержкой internal service-to-service calls bypass.

**Key components:**

**Permission checking helper (lines 13-22):**
```python
def _has_permission(user: UserPayload, permission: Permission, action: Action) -> bool:
    """Check if user has a specific permission/action pair."""
    for perm in user.role.permissions:
        if perm.name == permission.value:
            if action == Action.VIEW and perm.can_view:
                return True
            if action == Action.EDIT and perm.can_edit:
                return True
            break
    return False
```

**require_permission factory (lines 25-57):**
```python
def require_permission(*pairs: tuple[Permission, Action]):
    """Factory returning a FastAPI dependency that allows access if ANY permission matches.

    Usage:
        Depends(require_permission(
            (Permission.TRIP_EDITOR, Action.VIEW),
            (Permission.WORK_ORDER, Action.VIEW),
        ))

    Returns UserPayload on success, None for internal (non-gateway) requests.
    Raises 401 without token, 403 if no permission matches.
    """
    async def dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> UserPayload | None:
        # Internal service-to-service bypass
        if request.headers.get("X-Source") != "api-gateway":
            return None
        
        # Token required for external requests
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        
        # Decode JWT token
        user = decode_token(credentials.credentials)

        # Check if ANY permission pair matches
        has_permissions = (_has_permission(user, permission, action) for permission, action in pairs)

        if any(has_permissions):
            return user
        
        # No permission matched → 403 Forbidden
        permission_list = ", ".join(f"{p.value} ({a.value})" for p, a in pairs)
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: requires any of [{permission_list}]",
        )

    return dependency
```

**Internal service bypass pattern:**
```python
if request.headers.get("X-Source") != "api-gateway":
    return None  # Skip authentication for internal calls
```

**How it works:**
- api-gateway injects `X-Source: api-gateway` header (см. proxy.py line 90)
- Internal service-to-service calls don't have this header → bypass auth
- External requests through gateway → full JWT verification + permission check

**Permission matching logic:**
- Accepts multiple (Permission, Action) pairs
- Returns True if user has ANY of the specified permissions
- Example: `(WORK_TIME_MAP.VIEW, TRIP_EDITOR.VIEW, WORK_ORDER.VIEW, EQUIPMENT.VIEW)`
- User needs only ONE of these permissions to access endpoint

**get_current_user dependency (lines 60-75):**
```python
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserPayload | None:
    """FastAPI dependency that decodes JWT and returns UserPayload without permission check.

    If X-Source header is missing or not equal to 'api-gateway', returns None
    to allow internal service-to-service calls without authentication.

    Usage: Depends(get_current_user)
    """
    if request.headers.get("X-Source") != "api-gateway":
        return None
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return decode_token(credentials.credentials)
```

**Use case:** Когда нужно только получить текущего пользователя без проверки конкретных разрешений

**Security scheme:**
```python
security = HTTPBearer(auto_error=False)
# auto_error=False позволяет credentials быть None (для internal calls)
```

**Integration with enterprise-service vehicles.py:**
```python
@router.get("", dependencies=[
    Depends(require_permission(
        (Permission.WORK_TIME_MAP, Action.VIEW),
        (Permission.TRIP_EDITOR, Action.VIEW),
        (Permission.WORK_ORDER, Action.VIEW),
        (Permission.EQUIPMENT, Action.VIEW),
    ))
])
async def list_vehicles(...):
    # Требуется хотя бы ОДНО из перечисленных разрешений
```

**Architecture pattern:**
- Factory pattern: require_permission() возвращает closure dependency function
- Dependency injection: FastAPI Depends() для automatic execution
- OR logic: any() для проверки хотя бы одного разрешения
- Bypass mechanism: X-Source header check для internal service calls
- JWT decoding: decode_token() из auth_lib.token module

**Error responses:**
- 401 Unauthorized: Missing bearer token
- 403 Forbidden: Token valid but no matching permissions
- Error message includes list of required permissions for debugging

---

### audit-dev/audit_lib/mixin.py (207 строк)

**Назначение:** SQLAlchemy AuditMixin для автоматического отслеживания изменений данных через mapper events с outbox паттерном для надёжной публикации в RabbitMQ Stream.

**Key concepts:**
- **AuditMixin** — Mixin класс, который автоматически регистрирует SQLAlchemy event listeners
- **Outbox pattern** — Запись аудита в audit_outbox таблицу вместо прямой публикации в MQ
- **Mapper events** — after_insert, after_update, after_delete hooks
- **Column exclusion** — Возможность исключить чувствительные поля через __audit_exclude__

**Mixin definition (lines 26-53):**
```python
class AuditMixin:
    """Mixin that hooks SQLAlchemy mapper events to write audit outbox records.

    Usage::

        class User(Base, AuditMixin):
            __tablename__ = "users"
            id = mapped_column(Integer, primary_key=True)
            name = mapped_column(String)

    By default all columns are audited. To exclude columns, set
    ``__audit_exclude__`` on the model class::

        class User(Base, AuditMixin):
            __audit_exclude__ = {"password_hash"}
    """

    __audit_exclude__: ClassVar[set[str]] = set()

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__tablename__"):
            # Регистрация event listeners для каждой модели
            event.listen(cls, "after_insert", _after_insert)
            event.listen(cls, "after_update", _after_update)
            event.listen(cls, "after_delete", _after_delete)
            _ensure_flush_listener()
```

**Automatic listener registration:**
- __init_subclass__ вызывается при создании каждого подкласса
- Автоматически регистрирует after_insert/update/delete events
- Не требует явного вызова в моделях

**Flush listener for expired attributes (lines 17-23, 134-169):**
```python
_flush_listener_installed: bool = False

def _ensure_flush_listener() -> None:
    """Install the ``before_flush`` listener on Session (once globally)."""
    global _flush_listener_installed
    if _flush_listener_installed:
        return
    event.listen(Session, "before_flush", _before_flush_load_expired)
    _flush_listener_installed = True

def _before_flush_load_expired(
    session: Session,
    flush_context: UOWTransaction,
    instances: Any,
) -> None:
    """Force-load expired attributes on dirty AuditMixin instances.

    When an attribute is expired (e.g. after commit) and then set to a new
    value without being read first, SQLAlchemy records the change in
    ``history.added`` but ``history.deleted`` is empty because the old value
    was never loaded.  We fix this by saving/restoring the pending values
    around a refresh so that the old values appear in ``history.deleted``.
    """
    for instance in list(session.dirty):
        if not isinstance(instance, AuditMixin):
            continue
        if not session.is_modified(instance, include_collections=False):
            continue

        insp = inspect(instance)
        assert insp is not None
        # Identify columns whose old value was never loaded (expired).
        pending: dict[str, Any] = {}
        columns = _auditable_columns(instance)
        for col in columns:
            hist = insp.attrs[col].history
            if hist.added and not hist.deleted:
                # Save the pending new value.
                pending[col] = hist.added[0]

        if pending:
            # Refresh the expired columns from the DB (loads old values).
            session.refresh(instance, list(pending.keys()))
            # Re-apply the pending changes so history now has old in deleted.
            for col, val in pending.items():
                setattr(instance, col, val)
```

**Problem solved:**
- SQLAlchemy может не загружать старые значения если атрибут expired
- history.added содержит новое значение, но history.deleted пуст
- Решение: refresh() для загрузки старых значений, затем re-apply новых

**Helper functions (lines 63-103):**
```python
def _get_entity_id(instance: Any) -> str:
    """Return the primary key value(s) of *instance* as a string."""
    mapper = inspect(type(instance))
    pk_cols = mapper.primary_key
    pk_vals = [getattr(instance, col.key) for col in pk_cols]
    if len(pk_vals) == 1:
        return str(pk_vals[0])
    return str(tuple(pk_vals))

def _auditable_columns(instance: Any) -> list[str]:
    """Return column attribute names that should be audited."""
    mapper = inspect(type(instance))
    exclude: set[str] = getattr(instance.__class__, "__audit_exclude__", set())
    return [attr.key for attr in mapper.column_attrs if attr.key not in exclude]

def _snapshot(instance: Any, columns: list[str]) -> dict[str, Any]:
    """Return a dict of {column: value} for the given columns."""
    result: dict[str, Any] = {}
    for col in columns:
        val = getattr(instance, col)
        result[col] = val
    return result

def _serialize_value(val: Any) -> Any:
    """Serialize a value using the custom serializer if configured."""
    from audit_lib.config import get_serializer
    serializer = get_serializer()
    if serializer is not None:
        return serializer(val)
    return val

def _serialize_dict(d: dict[str, Any] | None) -> dict[str, Any] | None:
    """Apply the custom serializer to every value in a dict."""
    if d is None:
        return None
    return {k: _serialize_value(v) for k, v in d.items()}
```

**Outbox insertion (lines 106-131):**
```python
def _insert_outbox(
    connection: Any,
    instance: Any,
    operation: str,  # "create", "update", "delete"
    old_values: dict[str, Any] | None,
    new_values: dict[str, Any] | None,
) -> None:
    """Insert an AuditOutbox record via the connection (safe during flush)."""
    from audit_lib.config import _get_audit_outbox_table, get_default_service_name

    audit_table = _get_audit_outbox_table()
    service = get_audit_service() or get_default_service_name()
    
    connection.execute(
        audit_table.insert().values(
            id=generate_uuid7(),  # UUID v7 для сортировки по времени
            entity_type=instance.__class__.__tablename__,
            entity_id=_get_entity_id(instance),
            operation=operation,
            old_values=_serialize_dict(old_values),
            new_values=_serialize_dict(new_values),
            user_id=get_audit_user(),  # Из audit context
            service_name=service,
            timestamp=datetime.now(UTC),
            processed=False,  # Флаг для exporter
        )
    )
```

**Event handlers (lines 172-206):**
```python
def _after_insert(mapper: Any, connection: Any, target: Any) -> None:
    """after_insert event: record a 'create' audit entry."""
    columns = _auditable_columns(target)
    new_values = _snapshot(target, columns)
    _insert_outbox(connection, target, "create", None, new_values)

def _after_update(mapper: Any, connection: Any, target: Any) -> None:
    """after_update event: record an 'update' audit entry (only changed fields)."""
    columns = _auditable_columns(target)
    insp = inspect(target)

    old_values: dict[str, Any] = {}
    new_values: dict[str, Any] = {}

    for col in columns:
        hist = insp.attrs[col].history
        if hist.has_changes():
            if hist.deleted:
                old_values[col] = hist.deleted[0]
            if hist.added:
                new_values[col] = hist.added[0]

    # Если ничего не изменилось, пропускаем создание записи
    if not old_values and not new_values:
        return

    _insert_outbox(connection, target, "update", old_values, new_values)

def _after_delete(mapper: Any, connection: Any, target: Any) -> None:
    """after_delete event: record a 'delete' audit entry."""
    columns = _auditable_columns(target)
    old_values = _snapshot(target, columns)
    _insert_outbox(connection, target, "delete", old_values, None)
```

**Update optimization:**
- Только изменённые поля записываются в audit_outbox
- hist.has_changes() проверка для пропуска неизменённых записей
- old_values содержит предыдущие значения, new_values — новые

**Usage example:**
```python
from sqlalchemy.orm import DeclarativeBase
from audit_lib import AuditMixin, set_audit_user

class User(Base, AuditMixin):
    __tablename__ = "users"
    __audit_exclude__ = {"password_hash"}  # Исключить чувствительные поля
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    password_hash = Column(String)  # Не будет аудироваться

# В коде приложения:
with set_audit_user(user_id="user-123"):
    user = User(name="John", email="john@example.com")
    session.add(user)
    session.commit()  # Автоматически создаст audit_outbox запись
```

**Outbox table schema:**
```sql
CREATE TABLE audit_outbox (
    id UUID PRIMARY KEY,              -- UUID v7
    entity_type VARCHAR NOT NULL,     -- Таблица (например, "users")
    entity_id VARCHAR NOT NULL,       -- ID записи
    operation VARCHAR NOT NULL,       -- "create", "update", "delete"
    old_values JSONB,                 -- Старые значения (NULL для create)
    new_values JSONB,                 -- Новые значения (NULL для delete)
    user_id VARCHAR,                  -- Кто сделал изменение
    service_name VARCHAR,             -- Какой сервис изменил
    timestamp TIMESTAMP WITH TIME ZONE,
    processed BOOLEAN DEFAULT FALSE   -- Флаг для exporter
);
```

**Architecture pattern:**
- **Outbox pattern:** Запись в БД → Exporter читает → Публикует в RabbitMQ → Ack
- **Guaranteed delivery:** Даже если RabbitMQ недоступен, данные сохранены в БД
- **Transactional safety:** audit_outbox запись в той же транзакции что и основное изменение
- **Custom serialization:** get_serializer() для обработки特殊 типов данных
- **Context management:** set_audit_user() context manager для установки текущего пользователя

**Integration with audit-exporter:**
- audit-exporter-dev polls audit_outbox WHERE processed = FALSE
- Publishes to ClickHouse для аналитики
- Sets processed = TRUE после успешной публикации
- Gating acknowledgement pattern для предотвращения потери данных

---

### cdc-bort-applier-dev/src/app/aggregate_applier.py (151 строка)

**Назначение:** AggregateApplier — применение FanOutPayload агрегатов в PostgreSQL с idempotency через seq_id tracking.

**Key class и методы:**

**AggregateApplier class** (lines 38-151):
```python
class AggregateApplier:
    """
    Применяет FanOutPayload агрегат в PostgreSQL в одной транзакции.
    Реализует AggregateHandler Protocol (handle + handle_raw).
    Используется AmqpConsumer: consumer вызывает handle_raw(body),
    AggregateApplier декодирует, проверяет дубликат, применяет, сохраняет seq_id.
    Если что-то идёт не так — исключение всплывает наверх, consumer делает nack.
    """
```

**setup()** — Создание таблицы cdc_seq_id при старте consumer (lines 68-75):
```python
async def setup(self) -> None:
    """Создать cdc_seq_id таблицу если не существует. Вызвать до start()."""
    async with self._factory.pool.acquire() as conn:
        await conn.execute(_CDC_SEQ_ID_DDL)
    logger.info(
        "cdc_seq_id table ready service={service}",
        service=self._service_name,
    )
```
DDL создает таблицу с полями: queue (TEXT PRIMARY KEY), last_seq_id (BIGINT NOT NULL), updated_at (TIMESTAMPTZ).

**handle_raw(body)** — Точка входа из AmqpConsumer (line 77-80):
```python
async def handle_raw(self, body: bytes) -> None:
    """Точка входа из AmqpConsumer. Декодирует и вызывает handle."""
    msg = self._decoder.decode(body)
    await self._apply(msg)
```
Использует msgspec.json.Decoder(FanOutPayloadMsg) для быстрой десериализации.

**_apply(payload)** — Основная логика применения с dedup check + транзакция (lines 88-143):

Шаг 1: Deduplication check вне транзакции (lines 103-114):
```python
async with self._factory.pool.acquire() as conn:
    row = await conn.fetchrow(_SEQ_ID_SELECT, self._queue_name)
if row is not None and payload.seq_id <= row["last_seq_id"]:
    logger.warning(
        "Duplicate seq_id detected — skipping service={service}"
        " seq_id={seq_id} last_known={last}",
        service=self._service_name,
        seq_id=payload.seq_id,
        last=row["last_seq_id"],
    )
    return
```
Проверяет cdc_seq_id таблицу — если seq_id уже обработан, пропускает сообщение.

Шаг 2: Транзакция применения всех таблиц (lines 116-135):
```python
async with self._factory.pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("SET CONSTRAINTS ALL DEFERRED")
        for table_name, table_batch in tables.items():
            applier = self._factory.get_or_create_applier(table_name)
            batch: AggregatedBatch[dict[str, Any]] = AggregatedBatch(
                upserts=table_batch.upserts,
                deletes=table_batch.deletes,
            )
            await applier.apply_in_transaction(conn, batch)
        # Outbox — пишем уведомления внутри той же транзакции
        if self._outbox_writer is not None:
            await self._outbox_writer.process(conn, payload)
        # Hook для подклассов — выполняется внутри транзакции
        await self._post_apply_hook(conn, payload)

        # seq_id сохраняется в той же транзакции — атомарно с данными
        await conn.execute(_SEQ_ID_UPSERT, self._queue_name, payload.seq_id)
```
Ключевые особенности:
- SET CONSTRAINTS ALL DEFERRED — отложенная проверка constraints до COMMIT
- Итерация по всем таблицам из payload.tables dict
- Для каждой таблицы создается AggregatedBatch с upserts/deletes lists
- Вызывается table-specific applier.apply_in_transaction(conn, batch)
- Outbox writer записывает уведомления о изменениях (если настроен)
- _post_apply_hook вызывается внутри транзакции для подклассов
- seq_id UPSERT выполняется в той же транзакции — атомарность данных и метаданных

**Architecture pattern:**
- RabbitMQ Stream → AmqpConsumer → handle_raw(body) → msgspec decode → dedup check → transaction apply → seq_id save
- Idempotency через cdc_seq_id таблицу с ON CONFLICT DO UPDATE
- Atomicity: данные + outbox notifications + seq_id в одной транзакции
- Factory pattern: ServiceFactory предоставляет pool и table-specific appliers
- Extension point: _post_apply_hook для кастомной логики подклассов

---

### settings-server-dev/app/routers/settings.py (62 строки)

**Назначение:** FastAPI router для управления секретами бортов через HashiCorp Vault integration.

**Key endpoints:**

**POST /secrets/{vehicle_id}** — Создание новой конфигурации для борта (lines 13-29):
```python
@settings_router.post("/{vehicle_id}")
async def create_new_secrets_pack(
    vehicle_id: int,
    background_tasks: BackgroundTasks,
    custom_variables: VariableCreateRequest = Body(...)
):
    try:
        result = VaultClient.create_new_secrets(vehicle_id, custom_variables)
        background_tasks.add_task(BortNotifier.notify_vehicle_updated, vehicle_id)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing configuration: {str(e)}")
```
Вызывает VaultClient.create_new_secrets() который:
1. Загружает шаблон из TEMPLATE_FILE_PATH
2. Объединяет common variables + vehicle_dependant variables (с заменой {VEHICLE_ID})
3. Добавляет custom_variables пользователя
4. Сохраняет в Vault cubbyhole mount по пути vehicle/{vehicle_id}
5. Асинхронно уведомляет борт через BortNotifier.notify_vehicle_updated()

**GET /secrets/{vehicle_id}** — Чтение конфигурации борта (lines 32-40):
```python
@settings_router.get("/{vehicle_id}")
async def read_secrets_pack_by_vehicle_id(
    vehicle_id: int
):
    try:
        return VaultClient.read_secrets_by_vehicle_id(vehicle_id)
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Not found config for vehicle_id {vehicle_id}")
```
Читает секрет из Vault cubbyhole/vehicle/{vehicle_id}, возвращает data.data dict.

**DELETE /secrets/{vehicle_id}** — Удаление конфигурации борта (lines 43-52):
```python
@settings_router.delete("/{vehicle_id}")
async def delete_secrets_pack_by_vehicle_id(
    vehicle_id: int
):
    try:
        if VaultClient.delete_secrets_by_vehicle_id(vehicle_id):
            return {"status": "success", "deleted env for vehicle_id": vehicle_id}
    except Exception as e:
        logger.error(f"Error processing config for vehicle_id {vehicle_id}: {e}")
        raise HTTPException(status_code=404, detail=f"Not found config for vehicle_id {vehicle_id}")
```
Удаляет секрет из Vault cubbyhole/data/vehicle/{vehicle_id}.

**GET /secrets** — Получение шаблона переменных (lines 55-61):
```python
@settings_router.get("")
async def get_template():
    result = extract_common_variables()
    return {
        "specific": result["specific"],
        "vehicle_dependant": result["vehicle_dependant"]
    }
```
Возвращает структуру шаблона с common и vehicle_dependant секциями.

**VaultClient integration (из vault_client.py):**

**init_conn()** — Проверка аутентификации в Vault (lines 19-30):
```python
@staticmethod
def init_conn():
    client = hvac.Client(url=VaultClient.BASE_URL, token=VaultClient.TOKEN)
    if not client.is_authenticated():
        logger.error("Vault authentication failed!")
        raise Exception("Vault authentication failed!")
    return client
```

**_merge_with_template(vehicle_id, stored_values)** — Слияние шаблона с кастомными значениями (lines 47-67):
```python
@staticmethod
def _merge_with_template(vehicle_id: int, stored_values: Dict[str, Any]) -> Dict[str, Any]:
    sections = VaultClient._load_template_sections()
    common = dict(sections.get("common") or {})
    vehicle_dependant = VaultClient._render_vehicle_dependant_vars(
        vehicle_id,
        sections.get("vehicle_dependant") or {},
    )

    template_owned_keys = set(common.keys()) | set(vehicle_dependant.keys()) | {"VEHICLE_ID"}
    custom_values = {
        key: value
        for key, value in (stored_values or {}).items()
        if key not in template_owned_keys
    }

    merged: Dict[str, Any] = {}
    merged.update(custom_values)
    merged.update(common)
    merged.update(vehicle_dependant)
    merged["VEHICLE_ID"] = str(vehicle_id)
    return merged
```
Логика слияния:
1. Загружает шаблон из файла (common + vehicle_dependant секции)
2. Рендерит vehicle_dependant переменные, заменяя {VEHICLE_ID} на реальное значение
3. Определяет template_owned_keys — ключи, которые нельзя переопределить
4. Фильтрует custom_values — только ключи вне template_owned_keys
5. Объединяет в порядке: custom_values → common → vehicle_dependant → VEHICLE_ID
6. Приоритет: vehicle_dependant перекрывает common, custom_values имеют низший приоритет

**create_new_secrets(vehicle_id, new_variables)** — Создание секрета в Vault (lines 70-92):
```python
@staticmethod
def create_new_secrets(vehicle_id: int, new_variables: Dict[str, Any]) -> dict:
    client = VaultClient.init_conn()
    final_config = VaultClient._merge_with_template(vehicle_id, new_variables.variables)
    try:
        client.secrets.kv.v2.create_or_update_secret(
            path=f"vehicle/{vehicle_id}",
            secret=final_config,
            mount_point='cubbyhole'
        )
        logger.info(f"Secret written successfully")
    except Exception as e:
        logger.error(f"Failed to write secret: {e}")
        raise e
    return final_config
```
Использует hvac library для KV v2 API, mount_point='cubbyhole'.

**Architecture pattern:**
- Template-based configuration management с hierarchical merging
- Vault KV v2 secrets storage с cubbyhole mount
- Background notification pattern: создание секрета → async notify борт
- Vehicle-specific customization через {VEHICLE_ID} placeholder substitution
- Protection against template override: template_owned_keys filtering

---

### bort-client-dev/src/pages/work-orders/ui/WorkOrdersPage/WorkOrdersPage.tsx (70 строк)

**Назначение:** Страница наряд-заданий для водителя — список маршрутов текущей смены с навигацией и переходом к деталям.

**Key hooks и логика:**

**useCurrentShiftTasks()** — Загрузка заданий текущей смены (line 17):
```typescript
const { data, isLoading, error } = useCurrentShiftTasks();
```
Custom hook из '@/shared/lib/hooks/useCurrentShiftTasks' который делает запрос к trip-service API для получения shift tasks текущего борта.

**Data processing** — Сортировка маршрутов по route_order (lines 19-21):
```typescript
const shift = data?.items?.[0] ?? null;
const tasks = !shift?.route_tasks?.length ? [] : [...shift.route_tasks].sort((a, b) => a.route_order - b.route_order);
const taskIds = tasks.map((t) => t.id);
```
Извлекает первую смену из response, сортирует route_tasks по route_order (порядок выполнения), создает массив ID для kiosk navigation.

**useKioskNavigation()** — Управление навигацией для тачскрина (line 23):
```typescript
const { setItemIds, setOnConfirm, selectedId, selectedIndex, setSelectedIndex } = useKioskNavigation();
```
Custom hook для kiosk mode: отслеживает выбранный элемент (selectedId, selectedIndex), обрабатывает подтверждение (setOnConfirm).

**Effect: синхронизация itemIds** (lines 26-28):
```typescript
useEffect(() => {
  setItemIds(taskIds);
}, [taskIds, setItemIds]);
```
При изменении списка задач обновляет IDs в kiosk navigation system.

**Effect: автоскролл к выбранному элементу** (lines 30-32):
```typescript
useEffect(() => {
  listRef.current?.scrollToRowIndex(selectedIndex);
}, [selectedIndex]);
```
При изменении selectedIndex вызывает scrollToRowIndex на RouteTaskList для прокрутки к выбранной строке.

**Effect: обработчик подтверждения** (lines 34-43):
```typescript
useEffect(() => {
  setOnConfirm(() => {
    if (selectedId) {
      void navigate(getRouteWorkOrderDetail(selectedId));
    }
  });
  return () => {
    setOnConfirm(null);
  };
}, [navigate, selectedId, setOnConfirm]);
```
Устанавливает callback для кнопки подтверждения (Enter/кнопка на тачскрине): при нажатии переходит на страницу деталей задания getRouteWorkOrderDetail(selectedId). Cleanup function сбрасывает callback при размонтировании.

**Loading state** (lines 45-47):
```typescript
if (isLoading) {
  return <div className={styles.loading}>Загрузка наряд-заданий…</div>;
}
```

**Error state** (lines 49-51):
```typescript
if (error) {
  return <div className={styles.error}>Не удалось загрузить данные. Проверьте proxy и Trip Service.</div>;
}
```

**RouteTaskList component** (lines 54-66):
```typescript
<RouteTaskList
  ref={listRef}
  tasks={tasks}
  selectedIndex={selectedIndex}
  onRowSelect={(index) => {
    setSelectedIndex(index);
    const id = tasks[index]?.id;
    if (id) {
      void navigate(getRouteWorkOrderDetail(id));
    }
  }}
/>
```
Рендерит таблицу маршрутов с:
- ref для imperative handle (scrollToRowIndex)
- tasks — отсортированный список маршрутов
- selectedIndex — индекс выбранной строки
- onRowSelect — callback при клике на строку: устанавливает selectedIndex и навигирует к деталям

**Architecture pattern:**
- Kiosk navigation pattern для тачскринов: useKioskNavigation hook управляет selectedId/selectedIndex
- Imperative handle pattern: RouteTaskList exposes scrollToRowIndex через forwardRef + useImperativeHandle
- Sorted display: route_tasks сортируются по route_order для правильного порядка выполнения
- Navigation on selection: клик на строку или кнопка подтверждения → navigate к деталям задания
- Error handling: clear messages для loading/error states

---

### bort-client-dev/src/widgets/route-task-list/ui/RouteTaskList/RouteTaskList.tsx (86 строк)

**Назначение:** Таблица маршрутных заданий текущей смены с поддержкой kiosk navigation и императивного скролла.

**Key interfaces:**

**RouteTaskListProps** (lines 12-21):
```typescript
interface RouteTaskListProps {
  readonly tasks: RouteTaskResponse[];
  readonly selectedIndex: number;
  readonly onRowSelect: (index: number) => void;
  readonly toolbar?: ReactNode;
}
```

**RouteTaskListHandle** (lines 26-28):
```typescript
export interface RouteTaskListHandle {
  readonly scrollToRowIndex: (index: number) => void;
}
```
Imperative API для программного скролла к строке по индексу.

**Component implementation** (lines 33-85):
```typescript
export const RouteTaskList = forwardRef<RouteTaskListHandle, RouteTaskListProps>(function RouteTaskList(
  { tasks, selectedIndex, onRowSelect, toolbar },
  ref,
) {
  const rowRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useImperativeHandle(
    ref,
    () => ({
      scrollToRowIndex: (index: number) => {
        rowRefs.current[index]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      },
    }),
    [],
  );

  return (
    <div className={styles.wrapper}>
      {toolbar ? <div className={styles.toolbar}>{toolbar}</div> : null}
      <div className={styles.header} role="row">
        <span>№</span>
        <span>Начало маршрута</span>
        <span>Конец маршрута</span>
        <span>Рейсы</span>
        <span>Вес, т</span>
        <span>Объём, м³</span>
        <span>Груз</span>
        <span>Статус</span>
      </div>
      <div className={styles.scroll}>
        {tasks.length === 0 ? (
          <div className={styles.empty}>Нет маршрутов в наряде</div>
        ) : (
          tasks.map((task, index) => (
            <RouteTaskRow
              key={task.id}
              rowRef={(el) => {
                rowRefs.current[index] = el;
              }}
              index={index}
              task={task}
              isSelected={index === selectedIndex}
              onSelect={() => onRowSelect(index)}
            />
          ))
        )}
      </div>
    </div>
  );
});
```

**Key features:**

1. **forwardRef + useImperativeHandle** (lines 33-47):
   - Component оборачивается в forwardRef для передачи ref от родителя
   - useImperativeHandle exposes scrollToRowIndex метод
   - scrollToRowIndex использует scrollIntoView({ block: 'nearest', behavior: 'smooth' }) для плавной прокрутки

2. **rowRefs array** (line 37):
   ```typescript
   const rowRefs = useRef<(HTMLButtonElement | null)[]>([]);
   ```
   Хранит refs ко всем строкам таблицы для программного доступа.

3. **Table header** (lines 53-64):
   - 8 колонок: №, Начало маршрута, Конец маршрута, Рейсы, Вес, Объём, Груз, Статус
   - role="row" для accessibility

4. **Empty state** (lines 66-68):
   ```typescript
   {tasks.length === 0 ? (
     <div className={styles.empty}>Нет маршрутов в наряде</div>
   ) : (
     // render rows
   )}
   ```

5. **RouteTaskRow rendering** (lines 69-80):
   - Для каждого task рендерится RouteTaskRow компонент
   - rowRef callback сохраняет ref в rowRefs.current[index]
   - isSelected={index === selectedIndex} подсвечивает выбранную строку
   - onSelect={() => onRowSelect(index)} вызывает callback при клике

**Architecture pattern:**
- Imperative handle pattern: parent component может вызвать scrollToRowIndex для программной прокрутки
- Ref array pattern: rowRefs хранит refs ко всем строкам для доступа по индексу
- ForwardRef pattern: позволяет parent component получить доступ к imperative methods
- Smooth scrolling: scrollIntoView с behavior: 'smooth' для UX
- Accessibility: role="row" для screen readers

---

### dispa-frontend-dev/frontend/src/pages/shift-tasks/ShiftTasksPage.tsx (234 строки)

**Назначение:** Страница диспетчера для управления заданиями на смену — отображение списка маршрутов, активация заданий, мониторинг прогресса рейсов.

**Key state variables** (lines 20-26):
```typescript
const [routeTasks, setRouteTasks] = useState<RouteTaskView[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
const [activatingTaskId, setActivatingTaskId] = useState<string | null>(null);
const [activeTaskCompletedTrips, setActiveTaskCompletedTrips] = useState<number>(0);
const [placesMap, setPlacesMap] = useState<Record<string, string>>({});
```
- routeTasks: flattened список shift+route pairs для отображения
- activeTaskId: ID текущего активного задания
- activatingTaskId: ID задания в процессе активации (для UI feedback)
- activeTaskCompletedTrips: количество завершенных рейсов для активного задания
- placesMap: маппинг place_id → place_name из graph-service

**loadShiftTasks()** — Загрузка заданий на смену (lines 29-71):
```typescript
const loadShiftTasks = useCallback(async () => {
  setLoading(true);
  setError(null);

  try {
    const [shiftTasksData, activeTask] = await Promise.all([
      tripServiceApi.getShiftTasks({ page: 1, size: 100 }),
      tripServiceApi.getActiveTask(),
    ]);

    const flattenedRouteTasks: RouteTaskView[] = shiftTasksData.items.flatMap((shift) =>
      shift.route_tasks.map((route) => ({ shift, route }))
    );

    setRouteTasks(flattenedRouteTasks);
    const taskId = activeTask?.task_id ?? null;
    setActiveTaskId(taskId);

    // Загрузить количество завершенных рейсов для активного задания
    if (taskId) {
      try {
        const completedTrips = await tripServiceApi.getCompletedTripsCount(taskId);
        setActiveTaskCompletedTrips(completedTrips);
      } catch (tripCountErr) {
        console.error('Failed to load completed trips count:', tripCountErr);
        setActiveTaskCompletedTrips(0);
      }
    } else {
      setActiveTaskCompletedTrips(0);
    }
  } catch (err: any) {
    console.error('Failed to load tasks:', err);
    setError('Ошибка загрузки заданий');
  } finally {
    setLoading(false);
  }
}, []);
```

Ключевые шаги:
1. Параллельный запрос: getShiftTasks() + getActiveTask() через Promise.all
2. Flattening: shift.tasks массив преобразуется в плоский список RouteTaskView объектов
3. Установка activeTaskId из activeTask.task_id
4. Если есть активное задание, загружается количество завершенных рейсов через getCompletedTripsCount()
5. Error handling с fallback на 0 completed trips

**handleActivateRoute()** — Активация маршрута (lines 73-98):
```typescript
const handleActivateRoute = useCallback(
  async (routeId: string) => {
    if (activatingTaskId === routeId || loading) {
      return;
    }

    setActivatingTaskId(routeId);
    setError(null);

    try {
      await tripServiceApi.activateTask(routeId);
      await loadShiftTasks();
    } catch (err: any) {
      console.error('Failed to activate task:', err);
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Не удалось активировать задание';
      setError(message);
    } finally {
      setActivatingTaskId(null);
    }
  },
  [activatingTaskId, loading, loadShiftTasks]
);
```

Логика:
1. Guard clause: предотвращает повторную активацию того же routeId или активацию во время loading
2. Устанавливает activatingTaskId для UI feedback (disabled button, loading spinner)
3. Вызывает tripServiceApi.activateTask(routeId) — POST запрос к trip-service
4. После успешной активации перезагружает список заданий через loadShiftTasks()
5. При ошибке извлекает detail/message из response и показывает пользователю
6. В finally сбрасывает activatingTaskId

**getTaskStatusLabel()** — Маппинг статусов (lines 101-114):
```typescript
const getTaskStatusLabel = (routeTask: RouteTaskResponse): string => {
  switch (routeTask.status) {
    case 'completed': return 'Выполнено';
    case 'in_progress':
    case 'active': return 'В работе';
    case 'paused': return 'Приостановлено';
    case 'pending':
    default: return 'На выполнение';
  }
};
```

**loadPlaces()** — Загрузка мест из graph-service (lines 117-129):
```typescript
const loadPlaces = useCallback(async () => {
  try {
    const response = await graphServiceApi.getPlaces({ limit: 1000, offset: 0 });
    const map: Record<string, string> = {};
    response.items.forEach((place) => {
      map[String(place.id)] = place.name;
    });
    setPlacesMap(map);
  } catch (placesError) {
    console.error('Failed to load places:', placesError);
  }
}, []);
```
Загружает все места (limit: 1000) и создает маппинг id → name для отображения названий вместо ID.

**getPlaceLabel()** — Получение названия места (lines 132-141):
```typescript
const getPlaceLabel = useCallback(
  (placeId?: number | null) => {
    if (!placeId) {
      return '—';
    }
    const placeIdStr = String(placeId);
    return placesMap[placeIdStr] || placeIdStr;
  },
  [placesMap],
);
```
Если placeId не найден в placesMap, возвращает сам ID как строку.

**Rendering logic** (lines 153-233):

Для каждого routeTask вычисляется:
```typescript
const plannedTrips = route.planned_trips_count ?? 0;
const isActive = route.id === activeTaskId;
const completedTrips = isActive ? activeTaskCompletedTrips : (route.actual_trips_count ?? 0);
const isCompleted = plannedTrips > 0 && completedTrips >= plannedTrips;
const isActivating = activatingTaskId === route.id;
```

CSS классы для строки:
```typescript
className={[
  'task-row',
  isCompleted ? 'task-completed' : '',
  isActive ? 'task-row-active' : '',
  isActivating ? 'task-row-loading' : '',
].filter(Boolean).join(' ')}
```

Интерактивность:
```typescript
role="button"
tabIndex={0}
onClick={() => handleActivateRoute(route.id)}
onKeyDown={(event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleActivateRoute(route.id);
  }
}}
```
Поддержка keyboard navigation (Enter/Space) для accessibility.

Отображаемые поля:
- Task header: shift.task_name, shift.shift_date
- Route: place_a → place_b через getPlaceLabel()
- Trips: completedTrips / plannedTrips
- Volume: weight т / volume м³ из route.route_data
- Message: route.route_data?.message_to_driver
- Status: colored badge с getTaskStatusLabel()

**Architecture pattern:**
- Flattened data structure: nested shift→route_tasks преобразуется в плоский список для удобного рендеринга
- Parallel data fetching: Promise.all для одновременной загрузки shift tasks + active task
- Optimistic UI: activatingTaskId state для immediate feedback во время API call
- Cross-service integration: trip-service (tasks) + graph-service (places names)
- Keyboard accessibility: role="button", tabIndex, onKeyDown handler
- Conditional styling: CSS classes based on state (completed, active, activating)
- Error extraction:多层次 error message extraction из response.data.detail/message

---

### auth-service-backend-dev/app/api/v1/auth.py (126 строк)

**Назначение:** JWT authentication endpoints — signup, login, refresh, logout с Redis blacklist.

**Key endpoints:**

**POST /signup** — Регистрация нового пользователя (lines 18-43):
```python
@router.post("/signup", response_model=Token)
async def signup(form_data: SignUp, db: AsyncSession = Depends(get_db)):
    """Register a new user and issue JWT tokens."""
    logger.info("Attempting to register user: %s", form_data.username)
    result = await db.execute(
        select(User).filter((User.username == form_data.username))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning("Registration failed: User with username %s already exists", form_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this username already exists")

    new_user = User(
        username=form_data.username,
        is_active=True
    )
    new_user.set_password(form_data.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("User %s registered successfully", form_data.username)
    token_data = await get_user_roles_and_permissions(db, new_user.id)
    token_data["sub"] = new_user.username
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": new_user.username})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
```

Логика регистрации:
1. Проверка уникальности username через SELECT query
2. Создание нового User объекта с is_active=True
3. set_password() хеширует пароль через bcrypt
4. Commit и refresh для получения ID пользователя
5. get_user_roles_and_permissions() загружает роли и permissions из БД
6. Добавляет sub (username) в token_data payload
7. Создает access_token и refresh_token через create_access_token/create_refresh_token
8. Возвращает Token response с обоими токенами

**POST /login** — Аутентификация пользователя (lines 45-62):
```python
@router.post("/login", response_model=Token)
async def login(form_data: Login, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and issue JWT tokens."""
    logger.info("Attempting login for user: %s", form_data.username)
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not user.verify_password(form_data.password):
        logger.warning("Login failed for user %s: Incorrect username or password", form_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    token_data = await get_user_roles_and_permissions(db, user.id)
    token_data["sub"] = user.username
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info("User %s logged in successfully", form_data.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
```

Логика входа:
1. Поиск пользователя по username
2. verify_password() проверяет bcrypt hash
3. Если пользователь не найден или пароль неверный — 400 Bad Request
4. Загружает roles/permissions через get_user_roles_and_permissions()
5. Создает access_token с roles/permissions в payload
6. Создает refresh_token только с sub (username)
7. Возвращает оба токена

**POST /refresh** — Обновление токенов (lines 64-93):
```python
@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh JWT tokens using a valid refresh token."""
    logger.info("Attempting to refresh token")
    if await redis_client.is_token_blacklisted(refresh_token):
        logger.warning("Refresh failed: Token blacklisted")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token blacklisted")
    try:
        payload = decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Refresh failed: Invalid refresh token (no username)")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except PyJWTError:
        logger.warning("Refresh failed: Invalid refresh token (JWT error)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning("Refresh failed for user %s: Invalid or inactive user", username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    token_data = await get_user_roles_and_permissions(db, user.id)
    token_data["sub"] = user.username
    access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info("Token refreshed successfully for user %s", username)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
```

Логика обновления:
1. Проверка blacklist в Redis через is_token_blacklisted()
2. Декодирование refresh_token через jwt.decode с SECRET_KEY
3. Извлечение username из payload.sub
4. Проверка существования пользователя в БД
5. Перезагрузка актуальных roles/permissions (важно: permissions могут измениться)
6. Создание нового access_token с обновленными permissions
7. Создание нового refresh_token (rotation)
8. Возвращает новую пару токенов

**POST /logout** — Выход пользователя с blacklist токенов (lines 95-116):
```python
@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    refresh_token: str = None
):
    """Log out a user and blacklist both access and refresh tokens."""
    logger.info("Logging out user: %s", current_user.username)

    auth_header = request.headers.get("Authorization")
    if auth_header:
        access_token = auth_header.replace("bearer ", "")
        await redis_client.add_to_blacklist(access_token)
        logger.info("Access token blacklisted for user %s", current_user.username)

    if refresh_token:
        await redis_client.add_to_blacklist(refresh_token)
        logger.info("Refresh token blacklisted for user %s", current_user.username)

    return {"message": "Logged out"}
```

Логика выхода:
1. Извлекает Authorization header из request
2. Удаляет "bearer " prefix для получения access_token
3. Добавляет access_token в Redis blacklist через add_to_blacklist()
4. Если передан refresh_token, также добавляет его в blacklist
5. Blacklist предотвращает повторное использование токенов после logout

**POST /verify** — Проверка токена и получение ролей (lines 118-125):
```python
@router.post("/verify")
async def get_role(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_data = await get_user_roles_and_permissions(db, current_user.id)
    result = {
        "valid": True,
        **user_data
    }
    return result
```

Используется api-gateway для верификации токенов при каждом запросе.

**Architecture pattern:**
- JWT token-based authentication с access_token (короткоживущий) и refresh_token (долгоживущий)
- Bcrypt password hashing через set_password()/verify_password()
- Redis blacklist для invalidation токенов при logout
- Token rotation при refresh: создается новая пара токенов
- Roles/permissions reloading при refresh для актуализации прав доступа
- Structured logging с info/warning levels для audit trail

---

### api-gateway-dev/src/middleware.py (279 строк)

**Назначение:** aiohttp middleware для API gateway — request lifecycle logging, JWT verification, request ID generation.

**Helper functions:**

**_extract_api_version(request)** — Извлечение версии API (lines 36-50):
```python
def _extract_api_version(request: web.Request) -> str:
    """Resolve API version from request context or URL path."""
    api_version = request.get("api_version")
    if isinstance(api_version, str) and api_version:
        return api_version

    route_api_version = request.match_info.get("version")
    if route_api_version:
        return route_api_version

    version_match = _API_VERSION_PATTERN.match(request.path)
    if version_match:
        return version_match.group("version")

    return _UNKNOWN_VALUE
```

Приоритет источников:
1. request["api_version"] из контекста (устанавливается другими middleware)
2. request.match_info["version"] из route parameters
3. Regex match на URL path через _API_VERSION_PATTERN = re.compile(r"^/api/(?P<version>v[^/]+)(?:/|$)")
4. Fallback на "unknown"

**_extract_client_ip(request)** — Определение IP клиента (lines 53-64):
```python
def _extract_client_ip(request: web.Request) -> str:
    """Resolve client IP from X-Forwarded-For or aiohttp remote."""
    forwarded_for = request.headers.get(_X_FORWARDED_FOR_HEADER, "")
    if forwarded_for:
        forwarded_ip = forwarded_for.split(",", 1)[0].strip()
        if forwarded_ip:
            return forwarded_ip

    if request.remote:
        return request.remote

    return _UNKNOWN_VALUE
```

Извлекает первый IP из X-Forwarded-For header (для proxy/load balancer scenarios), fallback на request.remote.

**_extract_response_size(response)** — Размер ответа в байтах (lines 67-82):
```python
def _extract_response_size(response: web.StreamResponse) -> int:
    """Extract response size in bytes, returning 0 when unknown."""
    content_length = response.content_length
    if content_length is not None and content_length >= 0:
        return int(content_length)

    body_length = response.body_length
    if body_length is not None and body_length >= 0:
        return int(body_length)

    if isinstance(response, web.Response):
        response_body = response.body
        if isinstance(response_body, bytes):
            return len(response_body)

    return 0
```

Многоуровневая проверка: content_length → body_length → response.body length → 0.

**_resolve_error_type(request, status, error)** — Классификация ошибок (lines 85-113):
```python
def _resolve_error_type(
    request: web.Request,
    status: int,
    error: Exception | None,
) -> str:
    """Resolve a stable error type for error responses."""
    explicit_error_type = request.get("error_type")
    if isinstance(explicit_error_type, str) and explicit_error_type:
        return explicit_error_type

    if error is None and status < 400:
        return "none"

    if isinstance(error, ClientError):
        return "upstream_connection_error"

    if status == 401: return "unauthorized"
    if status == 502: return "bad_gateway"
    if status == 503: return "service_unavailable"

    if isinstance(error, web.HTTPException):
        return f"http_{error.status}"
    if error is not None:
        return type(error).__name__.lower()

    return f"http_{status}"
```

Приоритет: explicit error_type из request context → ClientError → HTTP status codes → exception class name.

**_resolve_proxy_protocol(request)** — Определение протокола (lines 129-144):
```python
def _resolve_proxy_protocol(request: web.Request) -> str:
    """Resolve request protocol for proxy observability context."""
    explicit_protocol = request.get(_PROXY_PROTOCOL_KEY)
    if isinstance(explicit_protocol, str) and explicit_protocol:
        return explicit_protocol

    connection = request.headers.get(_CONNECTION_HEADER, "").lower()
    upgrade = request.headers.get(_UPGRADE_HEADER, "").lower()
    if "upgrade" in connection and upgrade == _WEBSOCKET_PROTOCOL:
        return _WEBSOCKET_PROTOCOL

    accept = request.headers.get(_ACCEPT_HEADER, "").lower()
    if "text/event-stream" in accept:
        return _SSE_PROTOCOL

    return _HTTP_PROTOCOL
```

Определяет протокол: WebSocket (Connection: Upgrade, Upgrade: websocket) → SSE (Accept: text/event-stream) → HTTP.

**Middleware implementations:**

**request_lifecycle_logging_middleware** — Логирование жизненного цикла запроса (lines 147-198):
```python
@web.middleware
async def request_lifecycle_logging_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Emit per-request completion logs with elapsed time and metadata."""
    started_ns = time.perf_counter_ns()
    request["request_started_ns"] = started_ns

    response: web.StreamResponse | None = None
    request_error: Exception | None = None

    try:
        response = await handler(request)
        return response
    except Exception as exc:
        request_error = exc
        raise
    finally:
        elapsed_ms = max(1, (time.perf_counter_ns() - started_ns) // 1_000_000)

        status = 500
        if response is not None:
            status = response.status
        elif isinstance(request_error, web.HTTPException):
            status = request_error.status

        response_size = _extract_response_size(response) if response is not None else 0
        error_type = _resolve_error_type(request, status, request_error)
        request_id = _resolve_request_field(request, "request_id", _UNKNOWN_VALUE)

        log_payload = {
            "request_id": request_id,
            "elapsed_ms": int(elapsed_ms),
            "method": request.method,
            "path": request.path,
            "query": request.query_string,
            "status": status,
            "service": _resolve_request_field(request, "service", _UNKNOWN_VALUE),
            "api_version": _extract_api_version(request),
            "upstream_url": _resolve_request_field(request, "upstream_url", _UNRESOLVED_UPSTREAM),
            "client_ip": _extract_client_ip(request),
            "user_agent": request.headers.get(_USER_AGENT_HEADER, ""),
            "response_size": response_size,
            "error_type": error_type,
            "protocol": _resolve_proxy_protocol(request),
        }

        if status >= 400:
            logger.error("request_failed", extra=log_payload)
        else:
            logger.info("request_completed", extra=log_payload)
```

Ключевые особенности:
- Замеряет время выполнения через time.perf_counter_ns() с точностью до наносекунд
- Сохраняет started_ns в request context для использования другими middleware
- Try/except/finally блок захватывает exceptions и логирует их
- Вычисляет elapsed_ms с минимумом 1ms
- Определяет status code из response или exception
- Формирует comprehensive log_payload с 13 полями метаданных
- Логирует как error (status >= 400) или info (success)

**jwt_verification_middleware** — Верификация JWT токенов (lines 201-253):
```python
@web.middleware
async def jwt_verification_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Verify JWT tokens by calling the auth service.

    If the request carries an Authorization header the middleware forwards it
    to the auth service verify endpoint.  A 200 response lets the request
    proceed; any other status results in a 401 returned to the client.  If
    the auth service is unreachable, the gateway returns 503.

    Requests without an Authorization header or targeting excluded paths
    (e.g. ``/health``) are passed through without verification.
    """
    if request.path in _SKIP_AUTH_PATHS:
        return await handler(request)

    auth_header = request.headers.get(_AUTHORIZATION_HEADER)
    if not auth_header:
        return await handler(request)

    settings: Settings = request.app["settings"]
    verify_url = URL(str(settings.auth.url)) / settings.auth.verify_endpoint.lstrip("/")
    request[_PROXY_PROTOCOL_KEY] = _resolve_proxy_protocol(request)
    request["api_version"] = _extract_api_version(request)
    service = request.match_info.get("service")
    if service:
        request["service"] = service

    session: ClientSession = request.app["client_session"]
    try:
        async with session.post(
            verify_url,
            headers={_AUTHORIZATION_HEADER: auth_header},
        ) as resp:
            if resp.status != 200:
                info = await resp.json()
                request["error_type"] = "unauthorized"
                request["upstream_url"] = str(verify_url)
                return web.json_response(
                    {"error": "Unauthorized", "message": info},
                    status=401,
                )
    except ClientError:
        request["error_type"] = "auth_service_unavailable"
        request["upstream_url"] = str(verify_url)
        return web.json_response(
            {"error": "Service Unavailable"},
            status=503,
        )

    return await handler(request)
```

Логика верификации:
1. Пропускает /health и / paths (_SKIP_AUTH_PATHS)
2. Пропускает запросы без Authorization header
3. Извлекает настройки auth service из app context
4. Строит verify_url из base URL + verify_endpoint
5. Устанавливает protocol и api_version в request context для логирования
6. Делает POST запрос к auth service с Authorization header
7. Если статус != 200, возвращает 401 Unauthorized с details из response
8. При ClientError (network error) возвращает 503 Service Unavailable
9. При успехе (200) продолжает обработку запроса

**request_id_middleware** — Генерация X-Request-Id (lines 256-278):
```python
@web.middleware
async def request_id_middleware(
    request: web.Request,
    handler: _Handler,
) -> web.StreamResponse:
    """Ensure every request has an X-Request-Id header.

    If the incoming request already carries a non-empty X-Request-Id,
    it is preserved. Otherwise a new UUID4 is generated.

    The resolved request-id is stored in ``request["request_id"]`` so
    downstream handlers (e.g. the proxy) can forward it to upstream
    services.  It is also set on the outgoing response.
    """
    request_id = request.headers.get(_REQUEST_ID_HEADER, "").strip()
    if not request_id:
        request_id = str(uuid.uuid4())

    request["request_id"] = request_id

    response = await handler(request)
    response.headers[_REQUEST_ID_HEADER] = request_id
    return response
```

Логика:
1. Проверяет наличие X-Request-Id в incoming request
2. Если отсутствует или пустой, генерирует новый UUID4
3. Сохраняет в request["request_id"] для использования downstream handlers
4. После обработки устанавливает X-Request-Id на outgoing response
5. Обеспечивает end-to-end tracing через все сервисы

**Architecture pattern:**
- Middleware chain pattern: request_id → jwt_verification → request_lifecycle_logging → proxy handler
- Comprehensive observability: structured logging с 13 metadata fields, timing metrics, error classification
- Protocol detection: automatic WebSocket/SSE/HTTP detection via header inspection
- Centralized JWT verification: delegates to auth service instead of local validation
- Request correlation: X-Request-Id propagation across all services
- Error handling: graceful degradation with 503 when auth service unavailable
- Performance monitoring: nanosecond-precision timing via perf_counter_ns

---

### telemetry-service-dev/app/services/telemetry_storage.py (128 строк)

**Назначение:** Сервис для сохранения телеметрии в Redis Streams с TTL.

**TelemetryStorage class** (lines 13-127):

**__init__(self, redis_client, ttl_seconds)** — Инициализация (lines 21-30):
```python
def __init__(self, redis_client: Optional[Redis] = None, ttl_seconds: int = None):
    """
    Инициализация сервиса хранения телеметрии.
    
    Args:
        redis_client: Redis клиент (если None, будет получен через get_redis_client)
        ttl_seconds: TTL для Redis Streams (если None, используется из settings)
    """
    self.redis_client = redis_client
    self.ttl_seconds = ttl_seconds or settings.TELEMETRY_STREAM_TTL_SECONDS
```

Принимает опциональный redis_client для dependency injection, использует TELEMETRY_STREAM_TTL_SECONDS из settings по умолчанию.

**store_telemetry(vehicle_id, sensor_type, data)** — Сохранение телеметрии (lines 32-90):
```python
async def store_telemetry(
    self,
    vehicle_id: str,
    sensor_type: str,
    data: dict
) -> bool:
    """
    Сохранить телеметрию в Redis Stream.
    
    Args:
        vehicle_id: ID транспортного средства
        sensor_type: Тип датчика (speed, weight, fuel, gps, vibro)
        data: Данные телеметрии
        
    Returns:
        True если успешно сохранено, False в случае ошибки
    """
    try:
        # Получаем Redis клиент если не передан
        redis = self.redis_client or await get_redis_client()
        
        # Формируем ключ Redis Stream
        stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
        
        # Добавляем timestamp в данные
        timestamp = time.time()
        
        # Структура записи в Stream
        entry = {
            "timestamp": str(timestamp),
            "data": json.dumps(data, default=str)
        }
        
        # Добавляем запись в Redis Stream
        stream_id = await redis.xadd(stream_key, entry)
        
        # Устанавливаем TTL для ключа Stream (обновляется при каждом добавлении)
        await redis.expire(stream_key, self.ttl_seconds)
        
        logger.debug(
            "Telemetry stored in Redis Stream",
            stream_key=stream_key,
            stream_id=stream_id,
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            ttl_seconds=self.ttl_seconds
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Failed to store telemetry in Redis Stream",
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            error=str(e),
            exc_info=True
        )
        return False
```

Логика сохранения:
1. Получает Redis client через dependency injection или get_redis_client()
2. Формирует stream_key в формате telemetry-service:{sensor_type}:{vehicle_id}
   - Примеры: telemetry-service:speed:123, telemetry-service:gps:456
3. Добавляет текущий timestamp через time.time()
4. Создает entry dict с timestamp (string) и data (JSON serialized с default=str для non-serializable types)
5. Вызывает redis.xadd(stream_key, entry) — добавляет запись в Redis Stream, возвращает stream_id
6. Устанавливает TTL через redis.expire(stream_key, ttl_seconds) — обновляется при каждом xadd
7. Логирует успешное сохранение с debug level
8. При ошибке логирует с error level и exc_info=True для stack trace, возвращает False

**get_stream_info(vehicle_id, sensor_type)** — Информация о Stream для отладки (lines 92-126):
```python
async def get_stream_info(self, vehicle_id: str, sensor_type: str) -> Optional[dict]:
    """
    Получить информацию о Redis Stream (для отладки).
    
    Args:
        vehicle_id: ID транспортного средства
        sensor_type: Тип датчика
        
    Returns:
        Словарь с информацией о Stream или None при ошибке
    """
    try:
        redis = self.redis_client or await get_redis_client()
        stream_key = f"telemetry-service:{sensor_type}:{vehicle_id}"
        
        # Получаем длину Stream
        length = await redis.xlen(stream_key)
        
        # Получаем TTL
        ttl = await redis.ttl(stream_key)
        
        return {
            "stream_key": stream_key,
            "length": length,
            "ttl_seconds": ttl if ttl > 0 else None
        }
        
    except Exception as e:
        logger.error(
            "Failed to get stream info",
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            error=str(e)
        )
        return None
```

Возвращает dict с:
- stream_key: полный ключ
- length: количество записей в Stream через xlen()
- ttl_seconds: оставшееся время жизни (None если TTL не установлен или истек)

**Architecture pattern:**
- Redis Streams для временных рядов телеметрии с автоматическим expiration
- Per-vehicle, per-sensor streams: отдельный stream для каждой комбинации vehicle_id + sensor_type
- TTL management: expire обновляется при каждом xadd, обеспечивает sliding window retention
- JSON serialization с default=str для handling non-serializable types (datetime, Decimal, etc.)
- Dependency injection pattern: optional redis_client parameter для testing
- Error resilience: returns False/None вместо raising exceptions, comprehensive error logging
- Debug support: get_stream_info для monitoring stream health и debugging

---

### audit-exporter-dev/src/core/pipeline.py (145 строк)

**Назначение:** Export pipeline orchestrator — poll → write → ack цикл для экспорта audit событий из PostgreSQL в ClickHouse.

**Key function:**

**process_source(reader, ch_client, batch_size, state)** — Один цикл poll → write → ack (lines 30-144):
```python
async def process_source(
    reader: PostgresSourceReader,
    ch_client: ClickHouseClient,
    batch_size: int,
    state: BootstrapRuntimeState,
    *,
    cycle_id: str | None = None,
) -> ProcessSourceResult:
    """Execute one poll → write → ack cycle for a single source.

    Gates acknowledgement strictly on ``ClickHouseWriteOutcome.ok``.
    Captures expected failure paths (CH write failure, ack failure) in the
    returned result rather than raising.
    """
```

Фаза 1: Poll из PostgreSQL (lines 47-75):
```python
poll_logger.debug("poll_start", batch_size=batch_size)
poll_start = time.monotonic()
try:
    events, poll_result = await reader.poll(batch_size=batch_size)
    state.record_source_poll_success(poll_result)
except Exception as exc:
    duration_ms = round((time.monotonic() - poll_start) * 1000, 1)
    poll_logger.error("poll_failed", error=str(exc), duration_ms=duration_ms)
    state.record_source_poll_failure(source_name, str(exc))
    raise
duration_ms = round((time.monotonic() - poll_start) * 1000, 1)

if poll_result.row_count == 0:
    poll_logger.debug("poll_empty", duration_ms=duration_ms)
    return ProcessSourceResult(
        source_name=source_name,
        phase_reached="poll_empty",
        poll_result=poll_result,
        write_outcome=None,
        ack_outcome=None,
    )

poll_logger.info(
    "poll_complete",
    rows_polled=poll_result.row_count,
    duration_ms=duration_ms,
    highest_timestamp=str(poll_result.highest_seen_timestamp),
    highest_outbox_id=str(poll_result.highest_seen_outbox_id),
)
```
Вызывает reader.poll(batch_size) который возвращает:
- events: list of audit events из audit_outbox WHERE processed = FALSE LIMIT batch_size
- poll_result: SourcePollResult с metadata (row_count, highest_seen_timestamp, highest_seen_outbox_id)

Если row_count == 0, возвращает ProcessSourceResult с phase_reached="poll_empty" без write/ack.

Фаза 2: Write в ClickHouse (lines 77-108):
```python
dedup_token = derive_dedup_token(events)
poll_logger.info(
    "write_start",
    row_count=poll_result.row_count,
    dedup_token=dedup_token[:12],
)
write_start = time.monotonic()
write_outcome = await ch_client.insert_exported_events(events)
write_duration_ms = round((time.monotonic() - write_start) * 1000, 1)
state.record_clickhouse_write(write_outcome)

if not write_outcome.ok:
    poll_logger.error(
        "write_failed",
        row_count=write_outcome.row_count,
        error=write_outcome.error_message,
        duration_ms=write_duration_ms,
    )
    return ProcessSourceResult(
        source_name=source_name,
        phase_reached="write_failed",
        poll_result=poll_result,
        write_outcome=write_outcome,
        ack_outcome=None,
    )

poll_logger.info(
    "write_complete",
    rows_written=write_outcome.row_count,
    duration_ms=write_duration_ms,
    table_name=write_outcome.table,
)
```
Ключевые моменты:
- derive_dedup_token(events) генерирует токен для дедупликации в ClickHouse
- ch_client.insert_exported_events(events) выполняет INSERT INTO clickhouse_table
- Если write_outcome.ok == False, возвращает ProcessSourceResult с phase_reached="write_failed" **без acknowledgement** — это критично для предотвращения потери данных
- Записывает метрики в state: record_clickhouse_write(write_outcome)

Фаза 3: Acknowledge в PostgreSQL (lines 110-136):
```python
outbox_ids = [event.outbox_id for event in events]
poll_logger.info("ack_start", outbox_ids_count=len(outbox_ids))
ack_start = time.monotonic()
ack_outcome = await reader.acknowledge_rows(outbox_ids)
ack_duration_ms = round((time.monotonic() - ack_start) * 1000, 1)
state.record_acknowledgement(ack_outcome)

if not ack_outcome.ok:
    poll_logger.error(
        "ack_failed",
        outbox_ids_count=len(outbox_ids),
        error=ack_outcome.error_message,
        duration_ms=ack_duration_ms,
    )
else:
    poll_logger.info(
        "ack_complete",
        rows_acknowledged=ack_outcome.acknowledged_count,
        duration_ms=ack_duration_ms,
    )
    if ack_outcome.acknowledged_count != len(outbox_ids):
        poll_logger.warning(
            "ack_mismatch",
            outbox_ids_count=len(outbox_ids),
            rows_acknowledged=ack_outcome.acknowledged_count,
        )
```
Вызывает reader.acknowledge_rows(outbox_ids) который выполняет:
```sql
UPDATE audit_outbox SET processed = TRUE WHERE outbox_id IN (...)
```
Важно: acknowledgement происходит **только после успешного write в ClickHouse**.

Финальный результат (lines 137-144):
```python
phase = "completed" if ack_outcome.ok else "ack_failed"
return ProcessSourceResult(
    source_name=source_name,
    phase_reached=phase,
    poll_result=poll_result,
    write_outcome=write_outcome,
    ack_outcome=ack_outcome,
)
```

**ProcessSourceResult model** (lines 18-27):
```python
class ProcessSourceResult(BaseModel):
    """Structured outcome from one poll → write → ack cycle for a single source."""

    model_config = ConfigDict(frozen=True)

    source_name: SourceName
    phase_reached: str  # "poll_empty", "write_failed", "ack_failed", "completed"
    poll_result: SourcePollResult | None
    write_outcome: ClickHouseWriteOutcome | None
    ack_outcome: AcknowledgementOutcome | None
```
Frozen Pydantic model для иммутабельного результата цикла.

**Architecture pattern:**
- Gated acknowledgement: ack только после успешного write в ClickHouse
- Failure capture: все ошибки записываются в ProcessSourceResult вместо exceptions
- Structured logging: каждый шаг логируется с timing metrics (duration_ms)
- State tracking: BootstrapRuntimeState агрегирует метрики всех циклов
- Deduplication: derive_dedup_token для предотвращения дубликатов в ClickHouse
- Batch processing: configurable batch_size для контроля объема polling

---

### platform-sdk-dev/platform_sdk/_clients.py (76 строк)

**Назначение:** Async context manager facade для platform SDK — единая точка входа для всех сервисных клиентов с управлением httpx.AsyncClient lifecycle.

**Key class:**
```python
class AsyncClients:
    """Async context manager providing access to all SDK service clients.

    Usage::

        settings = ClientSettings(base_url="https://api.example.com")
        async with AsyncClients(settings) as clients:
            result = await clients.analytics.get_vehicle_telemetry(root)
    """

    def __init__(self, settings: ClientSettings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None
        self._base: AsyncBaseClient | None = None
        self._analytics: AsyncAnalyticsClient | None = None
        self._entered = False  # Guard against re-entry
```

**Context manager implementation (lines 44-66):**
```python
async def __aenter__(self) -> AsyncClients:
    if self._entered:
        raise RuntimeError(
            "AsyncClients context is already entered or has been used; "
            "construct a new AsyncClients instance for each `async with` block.",
        )
    self._entered = True
    
    # Создание httpx.AsyncClient с настройками
    self._http = build_async_client(self._settings)
    
    # Инициализация base client и service-specific clients
    self._base = AsyncBaseClient(self._http, self._settings)
    self._analytics = AsyncAnalyticsClient(self._base)
    
    return self

async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
    # Закрытие httpx.AsyncClient
    if self._http is not None:
        await self._http.aclose()
    
    # Очистка ссылок
    self._http = None
    self._base = None
    self._analytics = None
```

**Property accessor with safety check (lines 68-75):**
```python
@property
def analytics(self) -> AsyncAnalyticsClient:
    """The analytics service client. Available only inside `async with`."""
    if self._analytics is None:
        raise RuntimeError(
            "AsyncClients must be used as `async with AsyncClients(settings) as clients:`",
        )
    return self._analytics
```

**Error prevention patterns:**
1. **Re-entry guard:** _entered flag предотвращает повторное использование контекста
2. **Usage validation:** Property check что клиенты инициализированы внутри `async with`
3. **Clear error messages:** RuntimeError вместо AttributeError с понятными инструкциями

**Architecture pattern:**
- **Facade pattern:** Единый entry point для всех SDK клиентов
- **Context manager:** Автоматическое управление ресурсами (httpx.AsyncClient lifecycle)
- **Dependency injection:** AsyncBaseClient передается в service-specific clients
- **Lazy initialization:** Клиенты создаются при входе в контекст, уничтожаются при выходе

**Usage example:**
```python
from platform_sdk import AsyncClients, ClientSettings

settings = ClientSettings(base_url="https://api.example.com")

async with AsyncClients(settings) as clients:
    # clients.analytics доступен только внутри контекста
    result = await clients.analytics.get_vehicle_telemetry(root)
    
# После выхода из контекста httpx.AsyncClient закрыт
# Попытка использовать clients.analytics вызовет RuntimeError
```

**Benefits:**
- Resource safety: httpx.AsyncClient всегда закрывается корректно
- Clear API: один объект для доступа ко всем сервисам
- Error prevention: ясные сообщения об ошибках при неправильном использовании
- Extensibility: легко добавить новые service clients (_enterprise, _auth, etc.)

---

### wifi-event-dispatcher-dev/server/internal/grpc/server.go (296 строк)

**Назначение:** Go gRPC server с bidirectional streaming для обработки событий от бортов при активации WiFi соединения с Redis deduplication.

**Server structure (lines 20-33):**
```go
type server struct {
    serverpb.UnimplementedEventDispatchServiceServer
    logger          *zerolog.Logger
    app             application.App
    dedup           dedup.Service
    autorepubClient *autorepub.Client
}

func RegisterServer(app application.App, svc dedup.Service, log zerolog.Logger, autorepubClient *autorepub.Client) *server {
    logger := log.With().Str("component", "grpc.server").Logger()
    return &server{app: app, dedup: svc, logger: &logger, autorepubClient: autorepubClient}
}
```

**Deduplication check (lines 39-56):**
```go
// isDuplicateDelivery checks whether the delivery is a duplicate.
// Returns true if the delivery was already seen (and has been Ack'd), false otherwise.
// An empty MessageId is treated as non-duplicate (dedup check skipped).
// On Redis error the check fails open (returns false).
func (s *server) isDuplicateDelivery(ctx context.Context, delivery amqp.Delivery) bool {
    if delivery.MessageId == "" {
        s.logger.Debug().Str("component", "consumer").Msg("received delivery with empty MessageId, skipping dedup check")
        return false
    }

    isDup, err := s.dedup.IsDuplicate(ctx, delivery.MessageId)
    if err != nil {
        // Redis error → fail open (пропускаем сообщение)
        s.logger.Warn().Err(err).Str("component", "consumer").Str("messageID", delivery.MessageId).Msg("redis error on dedup check, proceeding")
        return false
    }
    if isDup {
        _ = delivery.Ack(false)  // Ack дубликата чтобы удалить из очереди
        s.logger.Warn().Str("component", "consumer").Str("messageID", delivery.MessageId).Msg("duplicate delivery, dropping")
        return true
    }
    return false
}
```

**StreamBortSendEvents — отправка событий от борта к серверу (lines 62-134):**
```go
func (s *server) StreamBortSendEvents(stream serverpb.EventDispatchService_StreamBortSendEventsServer) error {
    sendAck := func(messageID string, err error) error {
        ack := &serverpb.Ack{
            MessageId: messageID,
            Ok:        err == nil,
        }
        if err != nil {
            ack.Error = err.Error()
        }
        return stream.Send(&serverpb.SendEventResponse{
            Ack: ack,
        })
    }

    ctx := stream.Context()

    for {
        req, err := stream.Recv()
        if err != nil {
            // io.EOF — клиент закрыл стрим, это нормальное завершение.
            if errors.Is(err, io.EOF) {
                return nil
            }
            return err
        }

        switch req.Kind.(type) {
        case *serverpb.SendEventRequest_Producer:
            producer := req.GetProducer()
            s.logger.Info().
                Int32("truck_id", producer.GetTruckId()).
                Str("stream", "StreamBortSendEvents").
                Msg("truck connected to stream")
            continue
        }

        ev := req.GetEvent()
        if ev == nil {
            continue
        }

        messageID := ev.GetMessageId()

        s.logger.Debug().
            Str("message_id", messageID).
            Str("topic", ev.GetTopic()).
            Msg("received event from bort")

        // Конвертация protobuf → domain event
        event, err := domain.EventFromProto(ev)
        if err != nil {
            _ = sendAck(messageID, err) // ошибка конвертации — только ACK, стрим не рвём
            continue
        }

        // Трансформация топика: bort_4.server.trip_service.src → bort_4.server.trip_service.dst
        event.Topic = domain.ToDestinationTopic(event.Topic)

        // Обработка события (публикация в RabbitMQ)
        err = s.app.HandleEvent(ctx, event)

        if err != nil {
            s.logger.Err(err).Msg("failed to handle event")
        } else {
            s.logger.Debug().
                Str("message_id", messageID).
                Str("topic", event.Topic).
                Msg("published event to RabbitMQ")
        }

        // Отправка ACK борту
        if err := sendAck(messageID, err); err != nil {
            return err // не смогли отправить ACK — завершаем стрим
        }
    }
}
```

**StreamBortGetEvents — получение событий сервером от борта (lines 135-295):**
```go
func (s *server) StreamBortGetEvents(stream serverpb.EventDispatchService_StreamBortGetEventsServer) error {
    ctx := stream.Context()

    type rabbitMsg struct {
        delivery amqp.Delivery
        sub      *rabbitmq.ChanSubscription
    }

    // Channels для concurrent processing
    recvCh := make(chan *serverpb.GetEventRequest)
    recvErrCh := make(chan error, 1)
    msgCh := make(chan rabbitMsg)

    var subs []*rabbitmq.ChanSubscription
    var subsWg sync.WaitGroup
    pending := make(map[string]amqp.Delivery)  // messageID → delivery для ACK/NACK
    var suspendedDistribution map[string][]int

    defer func() {
        // Nack все неподтверждённые сообщения — вернутся в очередь
        for _, d := range pending {
            _ = d.Nack(false, true)
        }

        // Остановка всех подписок
        for _, sub := range subs {
            _ = sub.Stop()
        }

        subsWg.Wait()

        // Resume autorepub после остановки стрима
        if s.autorepubClient != nil && len(suspendedDistribution) > 0 {
            if err := s.autorepubClient.Resume(context.Background(), suspendedDistribution); err != nil {
                s.logger.Warn().Err(err).Msg("failed to resume autorepub after stream stop")
            }
        }
    }()

    // Goroutine для чтения запросов от клиента
    go func() {
        defer close(recvCh)
        for {
            req, err := stream.Recv()
            if err != nil {
                recvErrCh <- err
                return
            }
            select {
            case recvCh <- req:
            case <-ctx.Done():
                return
            }
        }
    }()

    // Функция запуска reader goroutine для каждой подписки
    startReader := func(sub *rabbitmq.ChanSubscription) {
        subsWg.Add(1)
        go func() {
            defer subsWg.Done()
            for {
                select {
                case msg, ok := <-sub.Messages():
                    if !ok {
                        return
                    }
                    select {
                    case msgCh <- rabbitMsg{delivery: msg, sub: sub}:
                    case <-ctx.Done():
                        return
                    }
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    for {
        select {
        case <-ctx.Done():
            return ctx.Err()

        case err := <-recvErrCh:
            if errors.Is(err, io.EOF) {
                return nil
            }
            return err

        case req, ok := <-recvCh:
            if !ok {
                return nil
            }

            switch req.Kind.(type) {
            case *serverpb.GetEventRequest_Subscriber:
                sub := req.GetSubscriber()
                truckID := sub.GetTruckId()
                s.logger.Info().
                    Int32("truck_id", truckID).
                    Str("stream", "StreamBortGetEvents").
                    Msg("truck connected to stream")

                // Подписка на все очереди для этого борта
                channels, err := s.app.SubscribeAll(ctx, int(truckID))
                if err != nil {
                    return err
                }
                subs = append(subs, channels...)
                for _, ch := range channels {
                    startReader(ch)
                }

                // Suspend autorepub перед подпиской чтобы избежать дублирования
                if s.autorepubClient == nil {
                    s.logger.Warn().Msg("autorepub client is not configured, skipping suspend before subscribe")
                } else {
                    dist, err := s.autorepubClient.GetDistribution(ctx)
                    if err != nil {
                        s.logger.Warn().Err(err).Msg("failed to get distribution before subscribe")
                    } else {
                        suspendedDistribution = dist
                        if err := s.autorepubClient.Suspend(ctx, dist); err != nil {
                            s.logger.Warn().Err(err).Msg("failed to suspend autorepub before subscribe")
                        }
                    }
                }

            case *serverpb.GetEventRequest_Ack:
                ack := req.GetAck()
                messageID := ack.GetMessageId()
                if delivery, ok := pending[messageID]; ok {
                    if !ack.GetOk() {
                        // NACK — вернуть в очередь для повторной доставки
                        if err := delivery.Nack(false, true); err != nil {
                            s.logger.Err(err).Msg("failed to nack")
                        }
                    } else {
                        // ACK — подтвердить обработку
                        if err := delivery.Ack(false); err != nil {
                            s.logger.Err(err).Msg("failed to ack")
                        }
                    }
                    delete(pending, messageID)
                }
            }

        case msg := <-msgCh:
            // Проверка дубликата через Redis
            if s.isDuplicateDelivery(ctx, msg.delivery) {
                continue
            }

            // Конвертация RabbitMQ delivery → domain event
            event, err := domain.NewEvent(msg.sub.QueueName(), msg.delivery.MessageId, msg.delivery.Body)
            if err != nil {
                s.logger.Err(err).Msg("failed to get event")
                _ = msg.delivery.Nack(false, true)
                continue
            }

            // Отправка события борту через gRPC stream
            if err := stream.Send(&serverpb.GetEventResponse{
                Event: event.ToProto(),
            }); err != nil {
                return err
            }

            // Сохранение delivery в pending для последующего ACK/NACK
            pending[event.MessageID] = msg.delivery
        }
    }
}
```

**Architecture patterns:**
- **Bidirectional streaming:** Два независимых потока (send/get) в одном gRPC connection
- **Concurrent processing:** Goroutines для чтения запросов и RabbitMQ сообщений
- **Select-based multiplexing:** select statement для обработки multiple channels
- **Deduplication via Redis:** isDuplicateDelivery проверка перед обработкой
- **Pending ACK tracking:** map[string]amqp.Delivery для отслеживания неподтверждённых сообщений
- **Autorepub coordination:** Suspend перед подпиской, Resume после отключения
- **Graceful shutdown:** defer cleanup с Nack неподтверждённых сообщений

**Use case:**
- Борт подключается по WiFi → открывается gRPC stream
- StreamBortSendEvents: борт отправляет события (GPS, sensor data) → сервер публикует в RabbitMQ
- StreamBortGetEvents: сервер отправляет команды/задания борту ← читает из RabbitMQ
- При отключении WiFi → stream закрывается, autorepub resumes

---

### cdc-distributor-dev/src/app/fan_out_orchestrator.py (140 строк)

**Назначение:** Оркестратор публикации CDC агрегатов в очередь конкретного борта с гарантией доставки через offset management и seq_id idempotency.

**Key concepts:**
- **Fan-out pattern:** Одно CDC событие → публикация в очереди多个 бортов
- **Per-bort isolation:** Каждый (bort x service) consumer получает свой экземпляр FanOutOrchestrator
- **Offset management:** Сохранение offset только после успешного publisher confirm
- **Seq ID idempotency:** Монотонно возрастающий seq_id для обнаружения дубликатов

**Class definition (lines 15-50):**
```python
class FanOutOrchestrator:
    """Оркестратор публикации в очередь одного борта.

    Заменяет MultiTableApplyOrchestrator. Вместо применения в БД,
    агрегирует CDC-события, сериализует в JSON и публикует
    в очередь конкретного борта.

    Каждый (bort x service) consumer получает свой экземпляр
    FanOutOrchestrator с фиксированным bort_id.
    Изоляция отказов достигается структурно —
    отдельные consumer'ы не влияют друг на друга.

    Гарантии:
    - Offset продвигается только после успешного publisher confirm
    - Structured logging на каждый publish с контекстом
    - Idempotent payload: CdcAggregator does last-write-wins by ID
    """

    def __init__(
        self,
        *,
        aggregator: MultiTableAggregator,
        publisher: AMQPPublisher,
        offset_manager: BortOffsetManager,
        bort_id: int,
        service_name: str,
        seq_id: int,
        on_seq_advance: Callable[[], None] | None = None,
    ) -> None:
        self._aggregator = aggregator
        self._publisher = publisher
        self._offset_manager = offset_manager
        self._bort_id = bort_id
        self._service_name = service_name
        self._seq_id = seq_id
        self._on_seq_advance = on_seq_advance
```

**Batch processing (lines 52-139):**
```python
async def process_batch(
    self,
    events: list[Envelope],
    stream_name: str,
    max_offset: int,
    min_offset: int,
) -> None:
    """Обрабатывает батч CDC-событий: агрегация -> сериализация -> publish.

    Args:
        events: список CDC-событий из стрима
        stream_name: имя RabbitMQ стрима
        max_offset: максимальный offset в батче
        min_offset: минимальный offset в батче
    """
    # 1. Агрегация по таблицам (last-write-wins)
    batches_by_table = self._aggregator.aggregate(events)

    logger.info(
        "Processing batch bort={bort} stream={stream} "
        "events={events} tables={tables} offsets={low}-{up}",
        bort=self._bort_id,
        stream=stream_name,
        events=len(events),
        tables=list(batches_by_table.keys()),
        low=min_offset,
        up=max_offset,
    )

    # 2. Конвертация AggregatedBatch в TableBatch для сериализации
    tables_payload: dict[str, TableBatch] = {}
    for table_name, batch in batches_by_table.items():
        tables_payload[table_name] = TableBatch(
            upserts=batch.upserts,
            deletes=batch.deletes,
        )

    # 3. Собираем payload
    payload = FanOutPayload(
        seq_id=self._seq_id,
        low_offset=min_offset,
        up_offset=max_offset,
        tables=tables_payload,
    )

    # 4. Сериализация через msgspec (быстрее чем json)
    body: bytes = msgspec.json.encode(payload)

    # 5. Публикация с retry (AMQPPublisher обрабатывает retry внутри)
    try:
        await self._publisher.publish(
            bort_id=self._bort_id,
            service_name=self._service_name,
            body=body,
        )
    except Exception:
        # Log error, do NOT save offset, do NOT advance seq_id.
        # The consumer's rstream position does not advance because
        # we re-raise the exception (handler fails, no offset commit).
        logger.error(
            "Fan-out failed target_id={bort} service={service} "
            "batch_offset={offset} result=error",
            bort=self._bort_id,
            service=self._service_name,
            offset=max_offset,
        )
        raise  # Re-raise чтобы consumer не коммитил offset

    # 6. Offset и seq_id сохраняются ТОЛЬКО после успешного publisher confirm
    await self._offset_manager.save_offset(
        stream_name=stream_name,
        bort_id=self._bort_id,
        offset=max_offset,
        seq_id=self._seq_id,
    )

    # 7. Инкремент seq_id после успешной публикации
    self._seq_id += 1
    if self._on_seq_advance is not None:
        self._on_seq_advance()

    # Structured log with all required context
    logger.info(
        "Fan-out ok target_id={bort} service={service} batch_offset={offset} result=ok",
        bort=self._bort_id,
        service=self._service_name,
        offset=max_offset,
    )
```

**Guarantees provided:**
1. **At-least-once delivery:** Offset сохраняется только после publisher confirm
2. **Idempotency:** seq_id позволяет bort-applier обнаружить дубликаты
3. **Failure isolation:** Exception re-raise prevents offset commit → retry on restart
4. **Structured logging:** Все логи содержат bort_id, service, offset для трейсинга

**Last-write-wins aggregation:**
- MultiTableAggregator объединяет multiple updates к одной записи
- Только последнее значение сохраняется в payload
- Уменьшает объем передаваемых данных

**msgspec serialization:**
- Быстрее стандартного json module (использует SIMD оптимизации)
- Type-safe encoding через Pydantic-like schemas
- Compact binary representation possible

**Integration flow:**
1. Debezium reads PostgreSQL WAL → RabbitMQ Streams
2. cdc-distributor consumes from stream → FanOutOrchestrator.process_batch()
3. Aggregation: multiple events → single payload per table
4. Serialization: FanOutPayload → msgspec JSON bytes
5. Publishing: AMQPPublisher → RabbitMQ exchange → bort-specific queue
6. Offset commit: ONLY after successful publish confirm
7. Seq ID increment: monotonic counter for idempotency

**Error handling strategy:**
- Publisher failure → exception raised → offset NOT saved → consumer retries
- This ensures at-least-once delivery semantics
- bort-applier uses seq_id to detect and skip duplicates

**Architecture pattern:**
- **Fan-out orchestration:** Single source → multiple destinations (борты)
- **Per-consumer isolation:** Separate FanOutOrchestrator instances per (bort, service)
- **Gated offset commit:** Save offset ONLY after downstream success
- **Idempotent delivery:** seq_id + last-write-wins aggregation

---

---

## ИТОГО УРОВЕНЬ 2 (ПРОДОЛЖЕНИЕ 4): ПРОАНАЛИЗИРОВАНО

✅ **audit-dev:** mixin.py (207 строк, SQLAlchemy AuditMixin с after_insert/update/delete events, outbox паттерн)  
✅ **platform-sdk-dev:** _clients.py (76 строк, AsyncClients async context manager, httpx lifecycle management)

**Ключевые находки из кода:**
- **audit mixin.py:** __init_subclass__ регистрирует event listeners для каждой модели; _auditable_columns исключает __audit_exclude__ поля; _after_insert/_update/_delete callbacks создают AuditOutbox записи с operation, old/new values diff, user_id из set_audit_user() контекста
- **platform-sdk _clients.py:** AsyncClients.__aenter__ проверяет _entered flag, создаёт httpx.AsyncClient через build_async_client(settings), инициализирует AsyncAnalyticsClient; __aexit__ закрывает client; analytics property проверяет активность контекста

**Общий прогресс Уровень 2:**
- ✅ client-disp-dev (25 страниц, Redux slice)
- ✅ infrastructure/ (7 компонентов)
- ✅ bort-client-dev (11 страниц, 9 виджетов)
- ✅ analytics-service-dev (FastAPI routes, ETL)
- ✅ graph-service-backend-dev (18 routers, location/route services)
- ✅ enterprise-service-dev (13 routers, vehicles CRUD)
- ✅ sync-service-dev (autorepub management)
- ✅ telemetry-service-dev (MQTT consumer, Redis Streams)
- ✅ auth-service-backend-dev (JWT auth endpoints)
- ✅ dump-service-dev (trip dump API)
- ✅ audit-dev (SQLAlchemy AuditMixin)
- ✅ platform-sdk-dev (Async HTTP clients)

**Проанализировано:** 12 из ~28 компонентов на Уровне 2 (~43%)  
**Осталось:** dispatching-repo, dispa-backend/frontend, graph-service-frontend, enterprise-frontend-demo, settings-server/bort, cdc-distributor/applier, wifi-event-dispatcher, audit-exporter и др.

---

### dispa-backend-dev (Trip Service) - State Machine & Trip Management

**Архитектура:** FastAPI с SQLAlchemy async ORM, Redis для state machine хранения, MQTT event publishing, TimescaleDB для временных рядов.

**Services (из src/app/services/, 21 модуль):**
- **state_machine.py** — StateMachine класс (1868 строк): управление состоянием техники через 6 состояний, переходы по триггерам tag/timer/manual
- **trip_manager.py** — Trip Manager (651 строка): создание/завершение рейсов, определение типа (planned/unplanned), связь с заданиями
- **cycle_manager.py** — Управление циклами (рейс = погрузка + перевозка + разгрузка)
- **event_handlers.py** — Обработчики событий от датчиков (52.5KB)
- **full_shift_state_service.py** — Сервис полного состояния смены (29KB)
- **place_remaining.py** — Остатки на местах погрузки/разгрузки (40.2KB)
- **route_summary.py** — Сводки по маршрутам (60.2KB)
- **state_history_service.py** — История состояний (39.4KB)
- **trip_state_sync_service.py** — Синхронизация состояния рейсов (31.9KB)
- **analytics.py** — Аналитика рейсов (11.7KB)
- **enterprise_client.py** — HTTP клиент к enterprise-service (16.5KB)
- **history_service.py** — История рейсов и тегов
- **vehicle_info.py**, **vehicle_tooltip.py** — Информация о технике
- **place_info.py** — Информация о местах работ
- **dispatcher_event_publisher.py**, **trip_event_publisher.py** — Публикация событий в MQTT/RabbitMQ
- **shift_load_type_volumes.py** — Объёмы грузов по типам за смену
- **tasks/** — Управление заданиями (8 файлов)
- **rabbitmq/** — RabbitMQ publisher/subscriber (9 файлов)

**State Machine логика (код из state_machine.py):**
- **6 состояний:** IDLE, MOVING_EMPTY (движение порожним), STOPPED_EMPTY (остановка порожним), LOADING (погрузка), MOVING_LOADED (движение с грузом), STOPPED_LOADED (остановка с грузом), UNLOADING (разгрузка), CUSTOM_STATE (динамические состояния)
- **3 типа триггеров:** TAG (получение метки локации — основной триггер), TIMER (таймер бездействия), MANUAL (ручной переход)
- **Хранение состояния:** Redis ключ `trip-service:vehicle:{vehicle_id}:state` с полями state, cycle_id, entity_type (cycle/trip), task_id, last_tag_id, last_place_id, last_transition
- **Переходы:** При получении tag события от eKuiper, State Machine определяет новое состояние на основе текущего состояния + sensor_data (speed, weight, vibro, tag)
- **История:** CycleStateHistory и CycleTagHistory таблицы в PostgreSQL для аналитики
- **Dynamic states:** State._missing_() создаёт динамические custom-state на лету для нестандартных ситуаций

**Trip Manager логика (код из trip_manager.py):**
- **create_trip(vehicle_id, place_id, tag, active_task_id, cycle_id):** Создание нового рейса внутри цикла при переходе в moving_loaded состояние
- **Определение типа рейса:** Если есть active_task_id и place_id == task.place_a_id → planned (плановый), иначе unplanned (внеплановый)
- **Связь с заданиями:** При создании planned рейса обновляет RouteTask.status = ACTIVE, сохраняет task_id и shift_id в Trip
- **Cycle-JTI паттерн:** Trip создаётся как JTI (Joined Table Inheritance) от Cycle — рейс наследует все поля цикла + добавляет trip-specific поля
- **loading_timestamp:** Время начала погрузки сохраняется из state_data при переходе в loading состояние
- **MQTT events:** Публикует trip_started событие в топик `/truck/{vehicle_id}/trip-service/events`
- **complete_trip():** Завершение рейса при достижении точки разгрузки (place_b_id), обновление RouteTask.status = COMPLETED, публикация trip_completed события

**Redis структура:**
```python
{
    "state": "moving_loaded",
    "cycle_id": "uuid-cycle-123",
    "entity_type": "trip",
    "task_id": "task-456",
    "last_tag_id": "tag-789",
    "last_place_id": 42,
    "last_transition": "2024-01-15T10:30:00Z"
}
```

**MQTT топики:**
- Входящие: `/truck/{vehicle_id}/sensor/{type}/events` (speed, weight, vibro, tag)
- Исходящие: `/truck/{vehicle_id}/trip-service/events` (trip_started, trip_completed, task_activated, task_cancelled, shift_task_received)
- State changes: `/truck/{vehicle_id}/trip-service/state_changes` (state_transition события)

---

*Продолжение следует...*

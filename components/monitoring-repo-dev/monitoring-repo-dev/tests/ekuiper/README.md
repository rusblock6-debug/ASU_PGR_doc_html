# Тесты eKuiper и PostgreSQL

Docker-based тесты для проверки всех правил eKuiper и интеграции с PostgreSQL.

## 🚀 Быстрый старт

```bash
# Из корня проекта

# 1. Запустить все сервисы
make dev-bort

# 2. Запустить тесты (с реальными данными)
make test-ekuiper

# 3. Запустить тесты с моками (БЕЗ реальных данных)
make test-ekuiper-with-mocks
```

## 🎭 Режимы работы

### Режим 1: Быстрые тесты (БЕЗ E2E, рекомендуется)
```bash
make test-ekuiper               # ~30 сек
make test-ekuiper-with-mocks    # ~30 сек, с моками
```
- ✅ Проверяет структуру БД, правила eKuiper, подключения
- ✅ Быстро работает (~30 секунд)
- ❌ Не проверяет полный цикл MQTT → БД

### Режим 2: Полные тесты (С E2E, медленно)
```bash
make test-ekuiper-full                  # ~2.5 мин
make test-ekuiper-with-mocks-full       # ~2.5 мин, с моками
```
- ✅ Проверяет полный цикл: MQTT → eKuiper → PostgreSQL
- ✅ Гарантирует корректность всей системы
- ❌ Медленно (~2.5 минуты)
- **Используйте перед релизом**

### Режим 3: С моками (для CI/CD)
```bash
make test-ekuiper-with-mocks            # БЕЗ E2E
make test-ekuiper-with-mocks-full       # С E2E
```
- **Публикует тестовые данные перед запуском**
- Не зависит от реальных устройств
- Работает на чистой системе

## 🧹 Очистка данных

### Автоматическая очистка (по умолчанию)
После каждого запуска тестов **автоматически удаляются**:
- Все записи с `bort='TEST_BORT'`, `'MOCK_TRUCK'`, `'DEBUG_TEST'`
- Все записи с `test_id` в metadata

```bash
make test-ekuiper-with-mocks
# После тестов:
# ✅ Удалено 127 тестовых записей
# 📊 Осталось записей в БД: 1543 (реальные данные)
```

### Ручная очистка
```sql
-- Удалить только тестовые данные
DELETE FROM telemetry.mqtt_raw_data 
WHERE raw_payload->'metadata'->>'bort' IN ('TEST_BORT', 'MOCK_TRUCK')
   OR raw_payload->'metadata' ? 'test_id';
```

## 📊 Что тестируется

### ✅ eKuiper (test_ekuiper_rules.py)
- **Стримы**: Проверка создания всех 13 стримов
- **Правила**: Проверка создания всех 14 правил
- **Статус**: Все правила в статусе `running`
- **External Services**: graphService зарегистрирован
- **Обработка**: mqtt_raw_to_jsonb обрабатывает данные

### ✅ PostgreSQL (test_postgres_integration.py)
- **Подключение**: PostgreSQL, TimescaleDB, PostGIS
- **Таблица**: mqtt_raw_data структура и данные
- **Топики**: /raw, /ds, /events присутствуют
- **Качество**: Нет NULL, корректные timestamp
- **Validation**: /validated топики больше не записываются

## 🔧 Опции запуска

```bash
# Полный вывод
docker compose -f docker-compose.bort.yaml run --rm pytest -vv

# Только конкретный тест
docker compose -f docker-compose.bort.yaml run --rm pytest test_ekuiper_rules.py

# Только конкретный класс
docker compose -f docker-compose.bort.yaml run --rm pytest test_ekuiper_rules.py::TestEKuiperRules

# Только один метод
docker compose -f docker-compose.bort.yaml run --rm pytest test_ekuiper_rules.py::TestEKuiperRules::test_all_rules_running

# С coverage
docker compose -f docker-compose.bort.yaml run --rm pytest --cov=.

# Останов на первой ошибке
docker compose -f docker-compose.bort.yaml run --rm pytest -x
```

## 📁 Структура

```
tests/ekuiper/
├── Dockerfile              # Docker образ для тестов
├── requirements.txt        # Python зависимости
├── pytest.ini             # Конфигурация pytest
├── conftest.py            # Fixtures
├── test_ekuiper_rules.py  # Тесты eKuiper
├── test_postgres_integration.py  # Тесты PostgreSQL
└── README.md              # Эта документация
```

## 🎯 Ожидаемый результат

```
========================= test session starts =========================
test_ekuiper_rules.py::TestEKuiperStreams::test_all_streams_created PASSED
test_ekuiper_rules.py::TestEKuiperRules::test_all_rules_created PASSED
test_ekuiper_rules.py::TestEKuiperRules::test_all_rules_running PASSED
test_ekuiper_rules.py::TestEKuiperRules::test_mqtt_raw_to_jsonb_processing PASSED
test_ekuiper_rules.py::TestEKuiperExternalServices::test_graph_service_registered PASSED
test_postgres_integration.py::TestPostgresConnection::test_postgres_is_running PASSED
test_postgres_integration.py::TestPostgresConnection::test_timescaledb_extension PASSED
test_postgres_integration.py::TestMqttRawDataTable::test_table_exists PASSED
test_postgres_integration.py::TestMqttRawDataTable::test_has_data PASSED
test_postgres_integration.py::TestMqttDataContent::test_no_validation_topics_in_recent_data PASSED

========================= 10 passed in 5.23s ==========================
```

## 🔍 Troubleshooting

### Тесты не подключаются к сервисам

```bash
# Проверить, что все сервисы запущены
docker ps

# Проверить логи
docker logs dispatching-ekuiper
docker logs dispatching-postgres
```

### Тесты падают с timeout

```bash
# Увеличить время ожидания в conftest.py
# или перезапустить сервисы
make stop
make dev-bort
```

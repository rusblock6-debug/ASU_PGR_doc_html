# Graph Service Backend

## Описание
Backend API для визуализации и управления графами дорожных сетей карьера. Сервис предоставляет REST API для работы с уровнями, узлами, ребрами и метками, real-time обновления позиций транспорта через WebSocket, интеграцию с MQTT для получения GPS данных.

## Основной функционал
- **REST API** для управления уровнями, узлами, ребрами и метками
- **WebSocket** через Flask-SocketIO для real-time обновлений позиции транспорта
- **MQTT Client** подписка на GPS топики грузовиков (`truck/+/sensor/gps/ds`)
- **PostGIS** для хранения и обработки геопространственных данных
- **Ladder Nodes** - автоматическое создание межуровневых соединений
- **Построение маршрутов** с использованием python-igraph
- **Alembic** для миграций базы данных с автозапуском
- **Swagger UI** для документации API

## API Endpoints

### OpenAPI Documentation
- `GET /api` - API информация и список endpoints
- `GET /api/docs` - Swagger UI интерактивная документация
- `GET /openapi.json` - OpenAPI 3.0 спецификация

### Health & Monitoring
- `GET /health` - Health check с MQTT статусом подключения

### Levels Management
- `GET /api/levels` - Получить список всех уровней
- `POST /api/levels` - Создать новый уровень
- `GET /api/levels/{id}` - Получить уровень по ID
- `DELETE /api/levels/{id}` - Удалить уровень со всеми объектами (каскадное удаление)
- `GET /api/levels/{id}/objects` - Получить информацию об объектах уровня
- `GET /api/levels/{id}/graph` - Получить полный граф уровня (узлы, ребра, метки)

### Nodes Management
- `POST /api/levels/{id}/nodes` - Создать новый узел на уровне
- `PUT /api/nodes/{id}` - Обновить узел (координаты, тип)
- `DELETE /api/levels/{id}/nodes/{node_id}` - Удалить узел и связанные ребра

### Edges Management
- `POST /api/levels/{id}/edges` - Создать новое ребро между узлами
- `DELETE /api/levels/{id}/edges/{edge_id}` - Удалить ребро

### Ladder Nodes (межуровневые соединения)
- `POST /api/levels/{id}/ladder-nodes` - Создать ladder узел с автогенерацией на соседних уровнях
- `GET /api/levels/{id}/ladder-nodes` - Получить все ladder узлы на уровне
- `DELETE /api/ladder-nodes/{id}` - Удалить ladder узел и все связанные узлы

### Tags Management
- `POST /api/tags` - Создать новую метку с радиусом действия
- `PUT /api/tags/{id}` - Обновить метку
- `DELETE /api/tags/{id}` - Удалить метку
- `GET /api/tags` - Получить список меток
- `GET /api/tags/{id}` - Получить метку по id
- `HEAD /api/tags/indexes` - Проидексировать метки для корректной работы движения техники

### Location & Routing
- `POST /api/location/find` - Найти ближайшую метку по координатам (Canvas координаты)
- `POST /api/route/find` - Построить маршрут между двумя узлами (межуровневый)
- `POST /api/route/tags` - Найти маршрут между метками (deprecated)
- `GET /api/graph/{id}/stats` - Получить статистику по графу уровня
- `POST /api/graph/{id}/rebuild` - Перестроить граф уровня (инвалидация кэша)

## WebSocket Events

### Client → Server
- `join_vehicle_tracking` - Присоединиться к комнате отслеживания транспорта

### Server → Client
- `vehicle_location_update` - Обновление позиции транспорта
  ```json
  {
    "vehicle_id": "4_truck",
    "lat": 58.178408,
    "lon": 59.80824,
    "height": -50.0,
    "timestamp": 1756442459
  }
  ```

## Установка и запуск

### Локальная разработка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Переменные окружения
cp .env.example .env
# Отредактируйте .env с вашими настройками

# Запуск миграций (автоматически при старте)
python run.py run --host 0.0.0.0 --port 5000

# Или запустить миграции вручную
python run.py upgrade
```

### Docker
```bash
# Сборка
docker build -t graph-service-backend .

# Запуск
docker run -p 5001:5000 \
  -e POSTGRES_HOST=postgres \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=dispatching \
  -e NANOMQ_HOST=nanomq \
  -e NANOMQ_MQTT_PORT=1883 \
  -e REDIS__REDIS_HOST=6379 \
  -e REDIS__REDIS_PORT=redis
  graph-service-backend
```

### CLI Commands
```bash
# Запустить сервер
python run.py run --host 0.0.0.0 --port 5000 --debug

# Инициализировать БД с демо-данными
python run.py init-db

# Проверить подключение к БД
python run.py test-db

# Создать миграцию
python run.py migrate

# Применить миграции
python run.py upgrade
```

## Конфигурация

### Обязательные переменные окружения

#### PostgreSQL Configuration
- `POSTGRES_HOST` - PostgreSQL хост (default: localhost)
- `POSTGRES_PORT` - PostgreSQL порт (default: 5432)
- `POSTGRES_USER` - PostgreSQL пользователь
- `POSTGRES_PASSWORD` - PostgreSQL пароль
- `POSTGRES_DB` - PostgreSQL база данных (должна иметь PostGIS расширение)

#### MQTT Configuration
- `NANOMQ_HOST` - NanoMQ MQTT брокер хост
- `NANOMQ_MQTT_PORT` - NanoMQ MQTT порт (default: 1883)

#### Redis Configuration
- `REDIS__REDIS_HOST` - Redis хост
- `REDIS__REDIS_PORT` - Redis порт (default: 6379)

### Опциональные переменные

#### Flask Configuration
- `DEBUG` - Режим отладки (default: false)
- `SECRET_KEY` - Flask секретный ключ для сессий

#### MQTT Authentication (опционально)
- `MQTT_USERNAME` - MQTT имя пользователя
- `MQTT_PASSWORD` - MQTT пароль

#### Deprecated
- `VEHICLE_ID` - ID транспортного средства (deprecated - извлекается из MQTT топика)

## Архитектура

### Технологический стек
- **Flask 3.0.0** - Web framework
- **Flask-SocketIO 5.3.6** - WebSocket сервер (threading mode)
- **Flask-CORS 4.0.0** - CORS поддержка
- **SQLAlchemy 2.0.23** - ORM для PostgreSQL (синхронная)
- **PostgreSQL + PostGIS** - Геопространственная база данных
- **GeoAlchemy2 0.14.2** - Геометрические типы для SQLAlchemy
- **Pydantic 2.5.0** - Валидация данных и схемы
- **Paho-MQTT 1.6.1** - MQTT клиент
- **python-igraph 0.11.5** - Построение графов и поиск путей
- **Alembic 1.13.1** - Миграции базы данных
- **Python 3.11** - Основная версия

### Архитектурные паттерны
- **Flask Application Factory** - `create_app()` для создания приложения
- **Flask Blueprints** - Организация API routes:
  - `api_bp` - основные CRUD операции для уровней, узлов, ребер
  - `crud_bp` - расширенные CRUD операции с валидацией
  - `ladder_bp` - управление межуровневыми соединениями
- **Pydantic Schemas** - Валидация входящих и исходящих данных
- **SQLAlchemy Models** - Декларативные модели с relationships
- **MQTT Client** - Фоновый поток для обработки GPS сообщений
- **WebSocket Handler** - Real-time broadcast обновлений позиций

## PostGIS Integration

Сервис использует PostGIS для работы с геопространственными данными:

### Геометрические типы
- **POINT** - Координаты узлов и меток (x, y, z)
- **LINESTRING** - Ребра графа между узлами
- **POLYGON** - Зоны действия меток (создаются через ST_Buffer с радиусом)

### Canvas координаты
⚠️ **Важно:** Сервис использует Canvas координаты в метрах, **НЕ GPS координаты**!
- x, y, z могут быть любыми числами (положительными или отрицательными)
- Евклидово расстояние используется для поиска ближайших меток
- SRID 4326 используется только для хранения в PostGIS
- Валидация координат отключена - Canvas система позволяет произвольные значения

### PostGIS функции
- `ST_Point()` - Создание точечной геометрии
- `ST_MakeLine()` - Создание линии между двумя точками
- `ST_Buffer()` - Создание зоны действия метки
- `ST_Distance()` - Вычисление расстояний (не используется, используется евклидово)

## MQTT Integration

Сервис подписывается на GPS топики всех грузовиков:

### MQTT Topics
- **Подписка:** `truck/+/sensor/gps/ds` - GPS данные всех грузовиков
- **Wildcard:** `+` - любой vehicle_id извлекается из топика

### Message Format
```json
{
  "data": {
    "lat": 58.178408,
    "lon": 59.80824,
    "height": -50.0
  },
  "metadata": {
    "bort": "AC26",
    "timestamp": 1756442459
  }
}
```

### Обработка
1. **Парсинг топика** - Извлечение vehicle_id из `truck/{vehicle_id}/sensor/gps/ds`
2. **Валидация данных** - Проверка наличия lat/lon (height опционально)
3. **Дедупликация** - Пропуск дубликатов за последние 5 секунд
4. **Сохранение в БД** - Создание записи VehicleLocation с PostGIS геометрией
5. **WebSocket broadcast** - Отправка обновления всем подключенным клиентам

### Auto-reconnect
- **Проверка подключения:** Каждые 10 секунд фоновый поток
- **Reconnect interval:** 5 секунд между попытками переподключения
- **Health check:** `/health` endpoint показывает статус MQTT подключения

## Ladder Nodes (межуровневые соединения)

Ladder узлы позволяют создавать вертикальные соединения между уровнями:

### Функционал
- **Автоматическая генерация** - Создаются на соседних уровнях (выше/ниже) с теми же x, y координатами
- **Связывание узлов** - `linked_nodes` JSON поле хранит ID связанных узлов: `{"above": node_id, "below": node_id}`
- **Вертикальные ребра** - Автоматически создаются ребра с `edge_type='vertical'` и `level_id=NULL`
- **Каскадное удаление** - Удаление ladder узла удаляет все связанные узлы на других уровнях

### Использование
```bash
# Создать ladder узел на уровне -50м с координатами (100, 200)
POST /api/levels/1/ladder-nodes
{
  "x": 100,
  "y": 200
}

# Автоматически создастся:
# - Узел на уровне -50м (текущий)
# - Узел на уровне -100м (если есть)
# - Узел на уровне 0м (если есть)
# - Вертикальные ребра между всеми узлами
```

## Валидация point_id в метках

Система обеспечивает полную валидацию уникальности и формата `point_id` на уровне Pydantic схем:

### Требования к формату point_id
- **Обязательное поле** - не может быть пустым или null
- **Уникальность** - каждый `point_id` должен быть уникален в рамках всех меток системы
- **Допустимые символы** - буквы (a-z, A-Z), цифры (0-9), дефис (-), подчеркивание (_)
- **Длина** - от 1 до 255 символов
- **Примеры валидных значений:**
  - `LOAD_POINT_1`
  - `dump-site-01`
  - `SHOVEL_A3`
  - `checkpoint_north`

### Этапы валидации
1. **Pydantic Field Validator** - Проверка формата (регулярное выражение)
2. **Database Uniqueness Check** - Проверка уникальности при создании/обновлении метки

### Ошибки валидации
```json
{
  "error": "Validation error",
  "details": {
    "point_id": "Метка с point_id 'LOAD_POINT_1' уже существует"
  }
}
```

## Разработка

### Hot Reload
Монтируй директорию приложения в docker-compose для development:
```yaml
volumes:
  - ./app:/app/app
  - ./config:/app/config
```

### Миграции
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# Просмотр истории
alembic history
```

### Тестирование
```bash
# Health check
curl http://localhost:5000/health

# Получить все уровни
curl http://localhost:5000/api/levels

# Создать уровень
curl -X POST http://localhost:5000/api/levels \
  -H "Content-Type: application/json" \
  -d '{"name": "Уровень -50м", "height": -50}'

# Swagger UI для интерактивного тестирования
# Открыть в браузере: http://localhost:5000/api/docs
```

### Структура проекта
```
graph-service-backend/
├── app/
│   ├── __init__.py                 # Flask application factory
│   ├── api/
│   │   ├── routes.py               # Основные API endpoints (levels, graph)
│   │   ├── crud_routes.py          # CRUD операции (nodes, edges, tags)
│   │   └── ladder_routes.py        # Ladder nodes endpoints
│   ├── models/
│   │   ├── database.py             # SQLAlchemy models
│   │   └── schemas.py              # Pydantic schemas
│   ├── mqtt/
│   │   ├── client.py               # MQTT клиент с auto-reconnect
│   │   └── websocket_handlers.py   # WebSocket event handlers
│   ├── services/
│   │   └── graph_service.py        # Бизнес-логика графов
│   ├── utils/
│   │   └── validation.py           # Валидация данных
│   └── static/
│       └── openapi.json            # OpenAPI спецификация
├── config/
│   └── database.py                 # Конфигурация PostgreSQL
├── migrations/                      # Alembic миграции
├── requirements.txt                # Python зависимости
├── alembic.ini                     # Alembic конфигурация
├── Dockerfile                      # Docker образ
└── run.py                          # CLI entrypoint
```

## Техническая спецификация

См. [task.md](task.md) для детальной технической спецификации включая:
- Схема базы данных
- API endpoint спецификации
- Требования к интеграции
- Требования к производительности

## Troubleshooting

### PostGIS не установлен
```bash
# Подключиться к PostgreSQL
psql -U postgres -d dispatching

# Установить расширение
CREATE EXTENSION IF NOT EXISTS postgis;
```

### MQTT не подключается
- Проверьте доступность NanoMQ брокера
- Проверьте переменные окружения NANOMQ_HOST и NANOMQ_MQTT_PORT
- Проверьте логи: `docker logs graph-service-backend --tail 50`

### WebSocket не работает
- Flask-SocketIO использует threading mode
- Убедитесь что CORS разрешен для вашего frontend
- Проверьте подключение к `/socket.io/` endpoint

# eKuiper Configuration - Mining Dispatch System

Конфигурация eKuiper для обработки потоковых данных телематики грузовиков с автоматической инициализацией.

## 📁 Структура файлов

```
ekuiper/
├── README.md                          # Этот файл - документация
├── Dockerfile                         # Кастомный образ с автоинициализацией
├── entrypoint.sh                      # Custom entrypoint для автозапуска
├── init/                              # 🔧 Автоматическая инициализация
│   ├── README.md                      # Документация по auto-init
│   ├── ruleset.json                   # Полный export streams + rules
│   ├── graphService.json              # External service конфигурация
│   └── init.sh                        # Скрипт автоинициализации
├── Sql.so                             # PostgreSQL sink plugin (56M)
├── ekuiper.sql.json                   # SQL Source метаданные (не используется)
├── ekuiper.sql.yaml                   # SQL Source конфиг (не используется)
├── graphService.json                  # External service (копия)
├── graphService.zip                   # Архив для регистрации
├── EKUIPER_EXTERNAL_SERVICES.md       # 📖 Полное руководство по External Services
└── rules-backup.json                  # Бэкап всех правил
```

## 🚀 Быстрый старт

### 1. Запустить eKuiper (с автоматической инициализацией)
```bash
docker compose -f docker-compose.bort.yaml up -d ekuiper
```

**Автоматически выполняется:**
- ✅ Импорт всех streams через Ruleset API
- ✅ Импорт всех rules через Ruleset API
- ✅ Регистрация graphService external function

Смотреть логи инициализации:
```bash
docker logs dispatching-ekuiper | grep -A 50 "eKuiper Auto-Initialization"
```

### 2. Проверить статус
```bash
# Список всех правил
curl http://localhost:9081/rules | jq '.'

# Статус конкретного правила
curl http://localhost:9081/rules/rule_tag_detection/status | jq '.'

# Список external functions
curl http://localhost:9081/services/functions | jq '.'
```

## 📊 Архитектура потока данных

```
                    ┌──────────────────┐
                    │  External NanoMQ │
                    │  (truck sensors) │
                    └────────┬─────────┘
                             │
                    ┌────────▼──────────┐
                    │  eKuiper STAGE 1  │
                    │  Proxy Rules      │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Local NanoMQ     │
                    │  /raw topics      │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  eKuiper STAGE 2  │
                    │  Downsampling     │
                    │  + Outlier Filter │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Local NanoMQ     │
                    │  /ds topics       │
                    └────┬───────┬──────┘
                         │       │
            ┌────────────┘       └───────────────┐
            │                                    │
   ┌────────▼──────────┐           ┌────────────▼──────────┐
   │ eKuiper STAGE 3   │           │ eKuiper STAGE 4       │
   │ Event Processing  │           │ Tag Detection         │
   │ (speed, weight)   │           │ (graphService API)    │
   └────────┬──────────┘           └────────────┬──────────┘
            │                                    │
   ┌────────▼──────────┐           ┌────────────▼──────────┐
   │  Event topics     │           │  tag/events topic     │
   │  (speed, weight,  │           │  (point detection)    │
   │   vibro, fuel)    │           │                       │
   └───────────────────┘           └───────────────────────┘
            │
            └──────────┐
                       │
            ┌──────────▼──────────┐
            │ eKuiper STAGE 5     │
            │ ALL MQTT Archive    │
            │ (#) → PostgreSQL    │
            └──────────┬──────────┘
                       │
            ┌──────────▼──────────┐
            │  PostgreSQL         │
            │  mqtt_raw_data      │
            │  (ВСЕ топики!)      │
            └─────────────────────┘
```

## 🔧 Основные правила

### STAGE 1: Proxy (External → Local Raw)
Перекладывает данные из внешнего NanoMQ в локальный, в `/raw` топики:
- `rule_proxy_gps` - GPS координаты
- `rule_proxy_speed` - Скорость
- `rule_proxy_weight` - Вес
- `rule_proxy_fuel` - Топливо

### STAGE 2: Downsampling (Raw → DS)
Фильтрация выбросов и downsampling в `/ds` топики (от ~10 Hz до ~2 Hz):
- `rule_downsample_speed` - фильтр: изменение ≤ 50%, нули только после ненулевых
- `rule_downsample_weight` - фильтр: изменение ≤ 50%, нули разрешены
- `rule_downsample_fuel` - фильтр: изменение ≤ 50%, нули разрешены
- `rule_downsample_gps` - без фильтрации (координаты могут резко меняться)

**Пример фильтра выбросов:**
```sql
WHERE lag(data->weight, 1, 0) = 0 
   OR abs(data->weight - lag(data->weight, 1, 0)) / 
      CASE WHEN lag(data->weight, 1, 1) = 0 THEN 1 
           ELSE lag(data->weight, 1, 1) END <= 0.5
-- Нули (нет груза) проходят фильтр, CASE защищает от деления на 0
```

### STAGE 3: Event Processing (DS → Events)
Обработка downsampled данных, генерация событий:
- `rule_speed_events` - moving/stopped статусы (из `speed_downsampled`)
- `rule_weight_events` - loaded/empty статусы (из `weight_downsampled`)
- `rule_vibro_events` - ⚠️ **ВАЖНО**: использует **RAW данные** (`local_stream_weight_ds`) для обнаружения быстрых изменений
  - active: дельта >= 2кг (ЛЮБОЕ резкое изменение веса)
  - inactive: стабильный вес (изменение < 2кг)
  - **Срабатывает при**: погрузке (0→200кг), разгрузке (200→0кг), вибрации (200→202кг)
- `rule_fuel_alerts` - алерты низкого уровня топлива (< 10%)

### STAGE 4: Tag Detection (GPS DS → Tag Events)
Определение меток по GPS координатам через external service:
- `rule_tag_detection` - вызывает graphService API для определения ближайшей метки

**SQL пример:**
```sql
SELECT 
  metadata->bort AS vehicle_id,
  'tag' AS sensor_type,
  metadata->timestamp AS timestamp,
  graphService('post', '/api/location/find', data) AS tag_response
FROM gps_downsampled
```

**API Request/Response:**
```json
// Request
{
  "lat": 58.170120,
  "lon": 59.829150
}

// Response
{
  "point_id": "TAG001",
  "point_name": "Точка погрузки",
  "point_type": "loading"
}
```

### STAGE 5: ПОЛНОЕ MQTT АРХИВИРОВАНИЕ (All Topics → PostgreSQL)
Архивирование **АБСОЛЮТНО ВСЕХ** MQTT топиков в PostgreSQL для долгосрочного хранения:

- `mqtt_raw_to_jsonb` - сохранение **ВСЕХ БЕЗ ИСКЛЮЧЕНИЯ** MQTT сообщений
  - Stream: `mqtt_stream` (wildcard `#` - **ВСЕ топики на NanoMQ**)
  - SQL: `SELECT now() as time, meta(topic) as topic, to_json(*) as raw_payload, false as processed FROM mqtt_stream`
  - Sink: SQL plugin → `telemetry.mqtt_raw_data`
  - Format: JSONB для гибкого хранения (использует **to_json()** для преобразования)
  - TimescaleDB: автоматическое партиционирование по времени

**ЧТО ИМЕННО СОХРАНЯЕТСЯ:**
- ✅ `/raw` - сырые данные с external NanoMQ
- ✅ `/ds` - downsampled данные (после фильтрации)
- ✅ `/events` - события (speed, weight, vibro, tag)
- ✅ `/alerts` - алерты (fuel low)
- ✅ **Системные топики** - $SYS/brokers/... и другие

**Зачем нужно:**
- Долгосрочное хранение **ВСЕХ** данных на каждом этапе pipeline
- Возможность ретроспективного анализа и отладки
- Backup данных на случай сбоя eKuiper
- Интеграция с BI системами и аналитикой
- Audit trail - полная история всех MQTT сообщений

## 🔌 External Service: graphService

### Конфигурация
```json
{
  "interfaces": {
    "graphService": {
      "address": "http://dispatching-graph-backend:5000",
      "protocol": "rest",
      "schemaless": true,
      "options": {
        "insecureSkipVerify": true,
        "headers": {
          "Content-Type": "application/json",
          "Accept": "application/json"
        }
      }
    }
  }
}
```

### Использование в SQL
```sql
graphService('post', '/api/location/find', data)
```

Где:
- `'post'` - HTTP метод
- `'/api/location/find'` - endpoint path
- `data` - JSON payload (весь объект data из GPS stream)

## 🧪 Тестирование

### Проверка правил
```bash
# Список всех правил с основными метриками
for rule in $(curl -s http://localhost:9081/rules | jq -r '.[].id'); do
  echo "=== $rule ==="
  curl -s http://localhost:9081/rules/$rule/status | jq '{status, records_in, records_out, exceptions}'
done
```

### Тестирование tag detection
```bash
# Подписаться на результат
docker run --rm --network=container:dispatching-nanomq \
  eclipse-mosquitto mosquitto_sub \
  -h localhost -p 1883 \
  -t 'truck/4_truck/sensor/tag/events' -v

# Отправить тестовое GPS сообщение
docker run --rm --network=container:dispatching-nanomq \
  eclipse-mosquitto mosquitto_pub \
  -h localhost -p 1883 \
  -t 'truck/4_truck/sensor/gps/ds' \
  -m '{"metadata":{"bort":"4_truck","timestamp":1234567893},"data":{"lat":58.170120,"lon":59.829150}}'
```

### Проверка external service
```bash
# Список всех external functions
curl http://localhost:9081/services/functions | jq '.'

# Детали graphService
curl http://localhost:9081/services/functions/graphService | jq '.'

# Тест доступности backend
docker exec dispatching-ekuiper wget -qO- http://dispatching-graph-backend:5000/health
```

## 🔄 Обновление конфигурации

### Редактировать конфигурацию

1. **Отредактировать `init/ruleset.json`** (streams и rules) или **`init/graphService.json`** (external service)
2. **Перезапустить контейнер:**
```bash
docker compose -f docker-compose.bort.yaml restart ekuiper
```

Init скрипт автоматически применит изменения!

### Экспорт текущей конфигурации
```bash
# Экспортировать все правила и стримы
curl http://localhost:9081/ruleset > config/ekuiper/init/ruleset.json
```

## 🔌 SQL Plugin для PostgreSQL

### Автоматическая загрузка через Bind Mount
SQL plugin загружается **автоматически из файла на хосте** через bind mount в `docker-compose.bort.yaml`.

**Конфигурация:**
```yaml
volumes:
  - ./config/ekuiper/Sql.so:/kuiper/plugins/sinks/Sql.so:ro
```

**Файл плагина:**
- **Путь на хосте**: `config/ekuiper/Sql.so` (56M)
- **Путь в контейнере**: `/kuiper/plugins/sinks/Sql.so`
- **Версия**: eKuiper 2.2.3, PostgreSQL support, Alpine-compatible
- **Сборка**: Собран внутри eKuiper контейнера для полной совместимости

**Как был собран плагин:**

SQL plugin был собран ВНУТРИ eKuiper контейнера для полной совместимости с Alpine Linux (musl libc).

См. полную инструкцию в разделе README про сборку плагина.

## 🐛 Troubleshooting

### External service недоступен
```bash
# Проверить доступность backend
docker exec dispatching-ekuiper wget -qO- http://dispatching-graph-backend:5000/health

# Проверить сеть
docker network inspect dispatching-repo_dispatching-network
```

### Stream не получает данные
```bash
# Проверить что данные есть в MQTT топике
docker run --rm --network=container:dispatching-nanomq \
  eclipse-mosquitto mosquitto_sub \
  -h localhost -p 1883 \
  -t 'truck/4_truck/sensor/gps/ds' -C 1 -v
```

### Правило не работает
```bash
# Проверить статус правила
curl http://localhost:9081/rules/rule_tag_detection/status | jq '.'

# Посмотреть последнюю ошибку
curl http://localhost:9081/rules/rule_tag_detection/status | jq -r '.op_4_project_0_last_exception'

# Проверить логи eKuiper
docker logs dispatching-ekuiper --tail 50 | grep -i error
```

### Пересоздать все правила
```bash
# Перезапустить контейнер (автоматически применит init/ruleset.json)
docker compose -f docker-compose.bort.yaml restart ekuiper

# Проверить что правила создались
docker logs dispatching-ekuiper | grep -A 20 "Initialization Summary"
```

## 📈 Метрики

### Метрики правил
```bash
# Все правила с основными метриками
for rule in $(curl -s http://localhost:9081/rules | jq -r '.[].id'); do
  echo "=== $rule ==="
  curl -s http://localhost:9081/rules/$rule/status | \
    jq '{status, records_in, records_out, exceptions}'
done
```

### Интерфейс
- eKuiper Manager UI: http://localhost:9083

## 💡 Best Practices

1. **Используй Ruleset Import API** для автоматической инициализации
2. **Используй schemaless** для простых REST API
3. **Передавай целый объект** (`data`) в external functions
4. **Мониторь exceptions** в статусе правил
5. **Используй downsampled streams** для уменьшения нагрузки на external API
6. **Фильтруй выбросы** для стабильности данных
7. **Тестируй через curl** перед созданием правил
8. **Делай бэкапы** конфигурации через REST API (экспорт ruleset)
9. **Документируй** изменения в правилах

## 📖 Документация

- [init/README.md](./init/README.md) - Документация по автоинициализации
- [EKUIPER_EXTERNAL_SERVICES.md](./EKUIPER_EXTERNAL_SERVICES.md) - Полное руководство по External Services
- [eKuiper Official Docs](https://ekuiper.org/docs/en/latest/)
- [External Functions](https://ekuiper.org/docs/en/latest/extension/external/external_func.html)
- [REST API](https://ekuiper.org/docs/en/latest/api/restapi/overview.html)
- [SQL Reference](https://ekuiper.org/docs/en/latest/sqls/overview.html)

## 📝 Changelog

### 2025-10-13 (v3)
- ✅ Исправлена логика вибрации: используется validated_stream_weight, убрано условие weight > 5.0
- ✅ Обновлена документация STAGE 6: полное MQTT архивирование
- ✅ Обновлен IP external NanoMQ: 10.100.109.26

### 2025-10-09 (v2)
- ✅ **Автоматическая инициализация** через Ruleset Import API
- ✅ Создана директория `init/` с ruleset.json и graphService.json
- ✅ Добавлен custom Dockerfile с entrypoint.sh
- ✅ Добавлен external service `graphService`
- ✅ Создано правило `rule_tag_detection`

### 2025-10-08 (v1)
- ✅ Базовая конфигурация eKuiper
- ✅ Правила proxy, validation, downsampling, events
- ✅ Фильтр выбросов (50%)
- ✅ SQL plugin для PostgreSQL
- ✅ Архивирование всех MQTT данных

---

**Версия:** 3.0  
**Последнее обновление:** 2025-10-13

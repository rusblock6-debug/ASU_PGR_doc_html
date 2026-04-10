# eKuiper Auto-Initialization

Автоматическая инициализация всех eKuiper сущностей при старте контейнера через нативный Ruleset Import API.

## Структура файлов

```
init/
├── README.md              # Этот файл
├── ruleset.json           # Полный export streams + rules (автоимпорт)
├── graphService.json      # External service конфигурация
└── init.sh                # Скрипт автоматической инициализации
```

## Как это работает

### 1. Автозапуск при старте контейнера

Docker compose запускает eKuiper с custom entrypoint:
```yaml
entrypoint: ["/bin/sh", "/entrypoint.sh"]
```

### 2. Entrypoint запускает init.sh

Файл `/entrypoint.sh`:
- Запускает eKuiper сервер в фоне
- Ожидает готовности eKuiper
- Выполняет `/kuiper/init/init.sh`
- Держит eKuiper процесс активным

### 3. Init.sh импортирует конфигурацию

Скрипт `init.sh`:
- Ожидает доступности eKuiper REST API (`/ping`)
- Подставляет `${VEHICLE_ID}` в ruleset.json через `sed`
- Импортирует ruleset через `POST /ruleset` (все streams/rules одним запросом)
- Регистрирует graphService через `POST /services`
- Выводит summary по созданным сущностям

## Преимущества решения

1. **Нативность**: использует официальный Ruleset Import API
2. **Declarative**: все в JSON файлах (Infrastructure as Code)
3. **Idempotent**: можно запускать многократно без ошибок
4. **Простота**: один JSON вместо десятков API вызовов
5. **Быстрота**: импорт ruleset в 10x быстрее чем по одному
6. **Версионирование**: легко отслеживать изменения в Git

## Ruleset.json структура

```json
{
  "streams": {
    "stream_name": "CREATE STREAM stream_name () WITH (...)"
  },
  "tables": {},
  "rules": {
    "rule_name": "{\"id\":\"rule_name\",\"sql\":\"...\",\"actions\":[...]}"
  }
}
```

### Streams

Все MQTT streams с разными конфигурациями:
- **external_stream_*** - чтение из внешнего NanoMQ
- **local_stream_***_ds - чтение из локального NanoMQ с downsampling
- **gps_downsampled** - специальный stream для tag detection

### Rules

Все правила обработки данных:
- **rule_proxy_*** - проксирование из внешнего в локальный NanoMQ
- **rule_downsample_*** - downsampling с фильтром выбросов (50%)
- **rule_*_events** - генерация событий (speed, weight, vibro, fuel)
- **rule_tag_detection** - определение меток через graphService API

## GraphService external function

External service для вызова graph-service-backend API:
```json
{
  "interfaces": {
    "graphService": {
      "address": "http://dispatching-graph-backend:5000",
      "protocol": "rest",
      "schemaless": true
    }
  }
}
```

Использование в SQL:
```sql
SELECT graphService('post', '/api/location/find', data) AS tag_response
FROM gps_downsampled
```

## Использование

### Первый запуск

```bash
docker compose up -d ekuiper
```

Автоматически:
1. Создаются все streams
2. Создаются все rules
3. Регистрируется graphService

### Проверка статуса

```bash
# Логи инициализации
docker logs dispatching-ekuiper | grep -A 50 "eKuiper Auto-Initialization"

# Список streams
curl http://localhost:9081/streams | jq 'keys'

# Список rules
curl http://localhost:9081/rules | jq '.[].id'

# External functions
curl http://localhost:9081/services/functions | jq '.'
```

### Изменение конфигурации

1. Отредактировать `ruleset.json` или `graphService.json`
2. Перезапустить контейнер:
```bash
docker compose restart ekuiper
```

Init скрипт автоматически применит изменения.

## Поведение при рестарте

- **Данные сохраняются** в volume `ekuiper-data:/kuiper/data`
- **Init.sh выполняется каждый раз** (idempotent)
- **Существующие правила не перезаписываются** (API возвращает 409 conflict)
- **Новые правила добавляются** если их нет

## Переменные окружения

### VEHICLE_ID

Динамическая подстановка vehicle_id во все правила:
```yaml
environment:
  VEHICLE_ID: "4_truck"  # Default
```

Init.sh заменяет `4_truck` на `${VEHICLE_ID}` во всех топиках:
```bash
sed "s/4_truck/${VEHICLE_ID}/g" ruleset.json
```

## Troubleshooting

### Init скрипт не выполняется

Проверить логи:
```bash
docker logs dispatching-ekuiper 2>&1 | grep "initialization"
```

### Правила не создаются

Проверить API доступность:
```bash
docker exec dispatching-ekuiper curl -s http://localhost:9081/ping
```

### External service не работает

Проверить доступность backend:
```bash
docker exec dispatching-ekuiper wget -qO- http://dispatching-graph-backend:5000/health
```

### Нужно пересоздать все правила

```bash
# Удалить все правила
for rule in $(curl -s http://localhost:9081/rules | jq -r '.[].id'); do
  curl -X DELETE http://localhost:9081/rules/$rule
done

# Перезапустить контейнер
docker compose restart ekuiper
```

## Миграция со старого init-rules-api.sh

Старый скрипт `init-rules-api.sh`:
- ✅ Сохранён для справки
- ❌ Больше не используется автоматически
- ✅ Можно запустить вручную если нужно

Новый подход:
- ✅ Автоматический запуск при старте
- ✅ Использует нативный Ruleset API
- ✅ Быстрее и проще

## Дополнительная информация

- [eKuiper Ruleset API](https://ekuiper.org/docs/en/latest/api/restapi/ruleset.html)
- [eKuiper External Services](./EKUIPER_EXTERNAL_SERVICES.md)
- [Project README](../README.md)


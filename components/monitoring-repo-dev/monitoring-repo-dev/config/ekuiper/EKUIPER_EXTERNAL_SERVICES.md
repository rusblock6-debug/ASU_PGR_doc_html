# eKuiper External Services - Полное руководство

## Содержание
1. [Введение](#введение)
2. [Типы External Services](#типы-external-services)
3. [Schemaless External Services](#schemaless-external-services)
4. [Schema-based External Services](#schema-based-external-services)
5. [Регистрация через REST API](#регистрация-через-rest-api)
6. [Использование в SQL правилах](#использование-в-sql-правилах)
7. [Практический пример: graphService](#практический-пример-graphservice)
8. [Troubleshooting](#troubleshooting)

---

## Введение

**External Services** в eKuiper позволяют вызывать внешние REST/gRPC API из SQL правил. Это мощный механизм для обогащения потоковых данных информацией из внешних систем.

### Основные возможности
- ✅ REST/gRPC/msgpack-rpc протоколы
- ✅ Schemaless (без proto файлов) и schema-based (с proto) режимы
- ✅ Динамическая передача параметров из SQL
- ✅ Парсинг JSON ответов
- ✅ Использование в SELECT, WHERE, JOIN

### Когда использовать
- Обогащение данных из внешних API
- Машинное обучение inference (ML models)
- Геокодирование, геолокация
- Валидация данных через внешние сервисы
- Интеграция с микросервисами

---

## Типы External Services

### 1. Schemaless (без схемы)
**Когда использовать:**
- ✅ Простые REST API с JSON
- ✅ Не хочется писать .proto файлы
- ✅ Быстрое прототипирование
- ✅ API без строгого контракта

**Ограничения:**
- ❌ Только REST протокол
- ❌ Меньше валидации на этапе конфигурации

### 2. Schema-based (с Protobuf схемой)
**Когда использовать:**
- ✅ gRPC API
- ✅ Строгая типизация и валидация
- ✅ Сложные структуры данных
- ✅ Production окружение

**Требования:**
- 📄 `.proto` файл с описанием API
- 📦 `google/api/annotations.proto` для HTTP mapping

---

## Schemaless External Services

### Структура конфигурации

```json
{
  "about": {
    "author": {
      "name": "Your Company",
      "email": "contact@example.com",
      "company": "Company Name",
      "website": "https://example.com"
    },
    "helpUrl": {
      "en_US": "https://docs.example.com",
      "ru_RU": "https://docs.example.com/ru"
    },
    "description": {
      "en_US": "Service description in English",
      "ru_RU": "Описание сервиса на русском"
    }
  },
  "interfaces": {
    "serviceName": {
      "address": "http://backend-service:5000",
      "protocol": "rest",
      "options": {
        "insecureSkipVerify": true,
        "headers": {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "Authorization": "Bearer YOUR_TOKEN"
        }
      },
      "schemaless": true
    }
  }
}
```

### Поля конфигурации

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `about` | object | ❌ | Метаинформация о сервисе |
| `interfaces` | object | ✅ | Описание интерфейсов сервиса |
| `interfaces.{name}` | object | ✅ | Конфигурация конкретного интерфейса |
| `address` | string | ✅ | URL базового адреса API |
| `protocol` | string | ✅ | Протокол: `rest`, `grpc`, `msgpack-rpc` |
| `schemaless` | boolean | ✅ | `true` для schemaless режима |
| `options` | object | ❌ | Дополнительные параметры |
| `options.headers` | object | ❌ | HTTP заголовки для запросов |
| `options.insecureSkipVerify` | boolean | ❌ | Пропустить проверку SSL сертификата |

### Использование в SQL

**Формат вызова:**
```sql
serviceName(method, endpoint, ...params)
```

**Параметры:**
1. `method` (string) - HTTP метод: `"post"`, `"get"`, `"put"`, `"delete"`
2. `endpoint` (string) - URL endpoint, например `"/api/location/find"`
3. `...params` - Параметры для передачи в API:
   - Отдельные значения: `lat, lon, height` → параметры URL или JSON body
   - Целый объект: `data` → весь объект становится JSON body

**Примеры:**

```sql
-- Передача отдельных параметров (становятся JSON body или URL params)
SELECT serviceName('post', '/api/endpoint', field1, field2, field3) FROM stream

-- Передача целого объекта (становится JSON body)
SELECT serviceName('post', '/api/endpoint', data) FROM stream

-- Передача вычисленных значений
SELECT serviceName('get', '/api/geocode', data->lat, data->lon) FROM stream
```

### Что происходит под капотом

**1. Отдельные параметры:**
```sql
graphService('post', '/api/location/find', 58.17, 59.82, -50)
```
→ HTTP POST `http://backend:5000/api/location/find`
```json
{
  "arg0": 58.17,
  "arg1": 59.82,
  "arg2": -50
}
```

**2. Объект целиком:**
```sql
graphService('post', '/api/location/find', data)
-- где data = {"lat": 58.17, "lon": 59.82}
```
→ HTTP POST `http://backend:5000/api/location/find`
```json
{
  "lat": 58.17,
  "lon": 59.82
}
```

---

## Schema-based External Services

### Структура конфигурации

```json
{
  "about": { ... },
  "interfaces": {
    "serviceName": {
      "address": "http://backend-service:5000",
      "protocol": "rest",
      "schemaType": "protobuf",
      "schemaFile": "service.proto",
      "functions": [
        {
          "name": "functionName",
          "serviceName": "rpc_method_name"
        }
      ],
      "options": {
        "insecureSkipVerify": true,
        "headers": {
          "Content-Type": "application/json"
        }
      }
    }
  }
}
```

### Protobuf Schema

**Базовый пример:**
```protobuf
syntax = "proto3";
package myservice;

service MyService {
  rpc FindTag(FindTagRequest) returns(FindTagResponse) {}
}

message FindTagRequest {
  double lat = 1;
  double lon = 2;
  double height = 3;
}

message FindTagResponse {
  string point_id = 1 [json_name="point_id"];
  string point_name = 2 [json_name="point_name"];
  string point_type = 3 [json_name="point_type"];
}
```

**С HTTP mapping (для REST API):**
```protobuf
syntax = "proto3";
package myservice;

import "google/api/annotations.proto";

service MyService {
  rpc FindTag(FindTagRequest) returns(FindTagResponse) {
    option (google.api.http) = {
      post: "/api/location/find"
      body: "*"
    };
  }
}

message FindTagRequest {
  double lat = 1;
  double lon = 2;
  double height = 3;
}

message FindTagResponse {
  string point_id = 1 [json_name="point_id"];
  string point_name = 2 [json_name="point_name"];
  string point_type = 3 [json_name="point_type"];
}
```

### Использование в SQL

```sql
-- Вызов schema-based функции
SELECT findTag(data->lat, data->lon, -50) AS result FROM stream
```

---

## Регистрация через REST API

### 1. Подготовка файлов

**Для schemaless:**
```bash
# Создать JSON конфигурацию
cat > myService.json << 'EOF'
{
  "about": { ... },
  "interfaces": {
    "myService": {
      "address": "http://backend:5000",
      "protocol": "rest",
      "schemaless": true,
      "options": { ... }
    }
  }
}
EOF

# Упаковать в ZIP
zip myService.zip myService.json
```

**Для schema-based:**
```bash
# Создать JSON конфигурацию и .proto файл
cat > myService.json << 'EOF'
{
  "interfaces": {
    "myService": {
      "address": "http://backend:5000",
      "protocol": "rest",
      "schemaType": "protobuf",
      "schemaFile": "myService.proto",
      "functions": [...]
    }
  }
}
EOF

cat > myService.proto << 'EOF'
syntax = "proto3";
...
EOF

# Упаковать оба файла
zip myService.zip myService.json myService.proto
```

### 2. Регистрация через API

**POST /services**
```bash
curl -X POST http://localhost:9081/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "myService",
    "file": "file:///tmp/myService.zip"
  }'
```

**Альтернатива - HTTP URL:**
```bash
curl -X POST http://localhost:9081/services \
  -H "Content-Type: application/json" \
  -d '{
    "name": "myService",
    "file": "http://example.com/myService.zip"
  }'
```

### 3. Проверка регистрации

**Список всех external functions:**
```bash
curl http://localhost:9081/services/functions | jq '.'
```

**Детали конкретной функции:**
```bash
curl http://localhost:9081/services/functions/myService | jq '.'
```

**Пример ответа:**
```json
{
  "FuncName": "myService",
  "ServiceName": "myService",
  "InterfaceName": "myService",
  "Addr": "http://backend:5000",
  "MethodName": "myService"
}
```

### 4. Обновление сервиса

```bash
curl -X PUT http://localhost:9081/services/myService \
  -H "Content-Type: application/json" \
  -d '{
    "name": "myService",
    "file": "file:///tmp/myService_v2.zip"
  }'
```

### 5. Удаление сервиса

```bash
curl -X DELETE http://localhost:9081/services/myService
```

---

## Использование в SQL правилах

### Базовый пример

```sql
SELECT 
  metadata->vehicle_id AS vehicle_id,
  metadata->timestamp AS timestamp,
  myService('post', '/api/endpoint', data) AS result
FROM my_stream
```

### Парсинг JSON ответа

Если API возвращает JSON, используй `parse_json()`:

```sql
SELECT 
  vehicle_id,
  parse_json(myService('post', '/api/endpoint', data)) AS parsed_result
FROM my_stream
```

**Доступ к полям:**
```sql
SELECT 
  vehicle_id,
  parse_json(myService('post', '/api/endpoint', data))->field_name AS value
FROM my_stream
```

### Условная фильтрация

```sql
SELECT * FROM my_stream
WHERE parse_json(myService('get', '/api/validate', data))->is_valid = true
```

### Использование в dataTemplate

```json
{
  "actions": [{
    "mqtt": {
      "topic": "output/topic",
      "dataTemplate": "{\"result\":{{if .api_result.point_id}}\"{{.api_result.point_id}}\"{{else}}null{{end}}}"
    }
  }]
}
```

### Обработка ошибок

```sql
SELECT 
  vehicle_id,
  CASE 
    WHEN myService('post', '/api/endpoint', data)->error IS NULL 
    THEN myService('post', '/api/endpoint', data)->result
    ELSE 'error'
  END AS safe_result
FROM my_stream
```

---

## Практический пример: graphService

### Задача
Определить метку (tag) по GPS координатам грузовика, вызывая API `graph-service-backend`.

### 1. Структура API

**Endpoint:** `POST /api/location/find`

**Request:**
```json
{
  "lat": 58.170120,
  "lon": 59.829150
}
```

**Response:**
```json
{
  "point_id": "TAG001",
  "point_name": "Точка погрузки",
  "point_type": "loading"
}
```

### 2. Конфигурация External Service

**graphService.json:**
```json
{
  "about": {
    "author": {
      "name": "Mining Dispatch System",
      "email": "contact@example.com"
    },
    "description": {
      "en_US": "Graph service tag detection API",
      "ru_RU": "API graph-service для определения меток"
    }
  },
  "interfaces": {
    "graphService": {
      "address": "http://dispatching-graph-backend:5000",
      "protocol": "rest",
      "options": {
        "insecureSkipVerify": true,
        "headers": {
          "Content-Type": "application/json",
          "Accept": "application/json"
        }
      },
      "schemaless": true
    }
  }
}
```

### 3. Регистрация

```bash
cd /tmp
cat > graphService.json << 'EOF'
{...конфигурация выше...}
EOF

zip graphService.zip graphService.json

curl -X POST http://localhost:9081/services \
  -H "Content-Type: application/json" \
  -d '{"name":"graphService","file":"file:///tmp/graphService.zip"}'
```

### 4. Создание Stream

```bash
curl -X POST http://localhost:9081/streams \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "CREATE STREAM gps_downsampled () WITH (
      DATASOURCE=\"truck/4_truck/sensor/gps/ds\", 
      FORMAT=\"json\", 
      TYPE=\"mqtt\", 
      CONF_KEY=\"local_ds\"
    );"
  }'
```

### 5. Создание Rule

```bash
curl -X POST http://localhost:9081/rules \
  -H "Content-Type: application/json" \
  -d '{
    "id": "rule_tag_detection",
    "sql": "SELECT metadata->bort AS vehicle_id, '\''tag'\'' AS sensor_type, metadata->timestamp AS timestamp, graphService('\''post'\'', '\''/api/location/find'\'', data) AS tag_response FROM gps_downsampled",
    "actions": [{
      "mqtt": {
        "server": "tcp://nanomq:1883",
        "topic": "truck/4_truck/sensor/tag/events",
        "qos": 0,
        "sendSingle": true,
        "dataTemplate": "{\"metadata\":{\"vehicle_id\":\"{{.vehicle_id}}\",\"sensor_type\":\"tag\",\"timestamp\":{{.timestamp}}},\"data\":{\"point_id\":{{if .tag_response.point_id}}\"{{.tag_response.point_id}}\"{{else}}null{{end}},\"point_name\":{{if .tag_response.point_name}}\"{{.tag_response.point_name}}\"{{else}}null{{end}},\"point_type\":{{if .tag_response.point_type}}\"{{.tag_response.point_type}}\"{{else}}null{{end}}}}"
      }
    }]
  }'
```

### 6. Тестирование

**Отправить тестовое GPS сообщение:**
```bash
mosquitto_pub -t 'truck/4_truck/sensor/gps/ds' \
  -m '{"metadata":{"bort":"4_truck","timestamp":1234567893},"data":{"lat":58.170120,"lon":59.829150}}'
```

**Подписаться на результат:**
```bash
mosquitto_sub -t 'truck/4_truck/sensor/tag/events' -v
```

**Ожидаемый результат:**
```json
{
  "metadata": {
    "vehicle_id": "4_truck",
    "sensor_type": "tag",
    "timestamp": 1234567893
  },
  "data": {
    "point_id": "TAG001",
    "point_name": "Точка погрузки",
    "point_type": "loading"
  }
}
```

### 7. Проверка статуса

```bash
curl http://localhost:9081/rules/rule_tag_detection/status | jq '{
  status: .status,
  gps_in: .source_gps_downsampled_0_records_in_total,
  processed: .op_4_project_0_records_in_total,
  published: .sink_mqtt_0_0_records_out_total,
  exceptions: .op_4_project_0_exceptions_total,
  last_error: .op_4_project_0_last_exception
}'
```

---

## Troubleshooting

### Проблема: "function XXX not found"

**Причина:** External service не зарегистрирован

**Решение:**
```bash
# Проверить список функций
curl http://localhost:9081/services/functions | jq '.'

# Зарегистрировать service
curl -X POST http://localhost:9081/services \
  -H "Content-Type: application/json" \
  -d '{"name":"myService","file":"file:///tmp/myService.zip"}'
```

### Проблема: "param must be a string" (schema-based)

**Причина:** Protobuf schema-based функции не работают корректно с REST API в текущей версии eKuiper

**Решение:** Используй **schemaless** режим:
```json
{
  "interfaces": {
    "myService": {
      "schemaless": true
    }
  }
}
```

### Проблема: "http executor fails to err http return code: 500"

**Причина:** Backend API возвращает ошибку

**Решение:**
```bash
# Проверить логи backend
docker logs dispatching-graph-backend 2>&1 | tail -50

# Проверить формат запроса
# В schemaless режиме передавай ВЕСЬ объект data, а не отдельные поля
graphService('post', '/api/endpoint', data)  # ✅ Правильно
graphService('post', '/api/endpoint', lat, lon, height)  # ❌ Неправильно для сложных API
```

### Проблема: Backend недоступен

**Причина:** Неправильный адрес или backend не запущен

**Решение:**
```bash
# Проверить доступность backend из контейнера eKuiper
docker exec dispatching-ekuiper wget -qO- --timeout=2 http://dispatching-graph-backend:5000/health

# Проверить docker network
docker network inspect dispatching-repo_dispatching-network
```

### Проблема: "open /kuiper/data/services/schemas/XXX.proto: no such file"

**Причина:** Proto файл не найден (для schema-based)

**Решение:**
```bash
# Скопировать .proto файл в контейнер
docker exec dispatching-ekuiper mkdir -p /kuiper/data/services/schemas
docker cp myService.proto dispatching-ekuiper:/kuiper/data/services/schemas/

# Или переключись на schemaless режим
```

### Проблема: Не приходят данные в stream

**Причина:** Stream не `SHARED` и используется в другом правиле

**Решение:**
1. Используй разные streams для разных правил
2. Или читай из результата предыдущего правила (например, из `/ds` топика)

```sql
-- Плохо: local_stream_gps_ds уже используется в rule_downsample_gps
CREATE STREAM my_stream () WITH (DATASOURCE="truck/4_truck/sensor/gps/raw", ...);

-- Хорошо: читай из downsampled топика
CREATE STREAM gps_downsampled () WITH (DATASOURCE="truck/4_truck/sensor/gps/ds", ...);
```

### Отладка запросов к API

**Включить debug логи backend:**
```bash
docker logs -f dispatching-graph-backend 2>&1 | grep -E "(POST|GET|location/find)"
```

**Проверить что именно отправляется:**
```bash
# Добавить debug в правило
SELECT 
  vehicle_id,
  data,  # Посмотреть что передаём
  graphService('post', '/api/location/find', data) AS result
FROM gps_downsampled
```

---

## Полезные ссылки

- [eKuiper External Functions](https://ekuiper.org/docs/en/latest/extension/external/external_func.html)
- [eKuiper REST API](https://ekuiper.org/docs/en/latest/api/restapi/services.html)
- [Protocol Buffers](https://protobuf.dev/)
- [gRPC HTTP Transcoding](https://cloud.google.com/endpoints/docs/grpc/transcoding)

---

## Заключение

External Services - мощный инструмент для интеграции eKuiper с внешними системами:

✅ **Используй schemaless** для быстрого прототипирования и простых REST API  
✅ **Передавай целый объект** (`data`) вместо отдельных полей для сложных API  
✅ **Парси JSON ответы** через `parse_json()` для доступа к полям  
✅ **Обрабатывай ошибки** через CASE WHEN или проверку на NULL  
✅ **Тестируй через curl** перед созданием правил  
✅ **Мониторь статус** правил через `/rules/{id}/status`

Для production окружения рассмотри schema-based подход с protobuf для строгой типизации и валидации.


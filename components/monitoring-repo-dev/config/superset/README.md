# Настройка Superset

## Подключение к Trino для доступа к PostgreSQL и ClickHouse

Trino позволяет объединять данные из PostgreSQL и ClickHouse в одном запросе.

### Шаг 1: Добавление Trino в Superset

1. Откройте Superset: http://localhost:8088
2. Войдите с учетными данными: `admin` / `admin`
3. Перейдите в **Settings** → **Database Connections** → **+ Database**
4. Выберите **Trino** из списка или введите вручную:
   - **Database Name**: `Trino`
   - **SQLAlchemy URI**: `trino://trino:8080/postgresql`
5. Нажмите **Test Connection**
6. Если тест успешен, нажмите **Connect**

### Шаг 2: Доступ к ClickHouse через Trino

После подключения Trino, вы можете использовать каталог `clickhouse` для запросов к ClickHouse:

**Важно:** В Superset используется одно подключение к Trino, но вы можете обращаться к разным каталогам (postgresql и clickhouse) в SQL запросах.

## Доступные каталоги в Trino

- `postgresql` - подключение к PostgreSQL БД
- `clickhouse` - подключение к ClickHouse БД

## Примеры SQL запросов

### 1. Запрос к PostgreSQL через Trino
```sql
SELECT * FROM postgresql.public.your_table LIMIT 10;
```

### 2. Запрос к ClickHouse через Trino
```sql
SELECT * FROM clickhouse.dispatching.your_table LIMIT 10;
```

### 3. Просмотр доступных таблиц в ClickHouse
```sql
SHOW TABLES FROM clickhouse.dispatching;
```

### 4. JOIN между PostgreSQL и ClickHouse
Объединение данных из разных БД в одном запросе:
```sql
SELECT
    p.id,
    p.name,
    c.metric_value,
    c.timestamp
FROM postgresql.public.users p
JOIN clickhouse.dispatching.metrics c ON p.id = c.user_id
WHERE c.timestamp >= CURRENT_DATE - INTERVAL '7' DAY
LIMIT 100;
```

### 5. Агрегация данных из ClickHouse
```sql
SELECT
    toDate(timestamp) as date,
    count(*) as total_events,
    avg(value) as avg_value
FROM clickhouse.dispatching.events
WHERE timestamp >= now() - INTERVAL 1 HOUR
GROUP BY toDate(timestamp)
ORDER BY date DESC;
```

### 6. Создание датасета в Superset

После подключения к Trino, создайте датасет:

1. Перейдите в **Data** → **Datasets** → **+ Dataset**
2. Выберите базу данных **Trino**
3. Выберите schema: `postgresql` или `clickhouse`
4. Выберите нужную таблицу
5. Нажмите **Create Dataset and Create Chart**

Теперь вы можете строить графики на основе данных из PostgreSQL или ClickHouse!

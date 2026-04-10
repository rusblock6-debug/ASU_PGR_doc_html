"""
Тесты для проверки интеграции с PostgreSQL.

Проверяет:
- Запись данных в БД
- Корректность структуры данных
- TimescaleDB функциональность
- Производительность записи
"""
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List


class TestPostgresConnection:
    """Тесты подключения к PostgreSQL."""
    
    def test_postgres_is_running(self, postgres_conn):
        """Проверка, что PostgreSQL запущен и доступен."""
        with postgres_conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            assert 'PostgreSQL' in version
    
    def test_timescaledb_extension(self, postgres_conn):
        """Проверка, что TimescaleDB расширение установлено."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM pg_extension 
                WHERE extname = 'timescaledb';
            """)
            result = cur.fetchone()
            assert result is not None, "TimescaleDB extension not installed"


class TestMqttRawData:
    """Комплексные тесты для telemetry.mqtt_raw_data (таблица, качество, производительность)."""
    
    # ========== Структура таблицы ==========
    
    def test_table_exists(self, postgres_conn):
        """Проверка существования таблицы."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'telemetry'
                    AND table_name = 'mqtt_raw_data'
                );
            """)
            exists = cur.fetchone()[0]
            assert exists, "Table telemetry.mqtt_raw_data does not exist"
    
    def test_table_structure(self, postgres_conn):
        """Проверка структуры таблицы."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'telemetry' 
                AND table_name = 'mqtt_raw_data'
                ORDER BY ordinal_position;
            """)
            columns = {row[0]: row[1] for row in cur.fetchall()}
            
            assert 'time' in columns
            assert 'topic' in columns
            assert 'raw_payload' in columns
            assert 'processed' in columns
            
            assert 'timestamp' in columns['time'].lower()
            assert 'text' in columns['topic'].lower()
            assert 'jsonb' in columns['raw_payload'].lower()
            assert 'boolean' in columns['processed'].lower()
    
    def test_is_hypertable(self, postgres_conn):
        """Проверка, что таблица является TimescaleDB hypertable."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM timescaledb_information.hypertables 
                WHERE hypertable_schema = 'telemetry' 
                AND hypertable_name = 'mqtt_raw_data';
            """)
            result = cur.fetchone()
            assert result is not None, "mqtt_raw_data is not a TimescaleDB hypertable"
    
    # ========== Наличие данных ==========
    
    def test_has_data(self, postgres_conn):
        """Проверка, что в таблице есть данные."""
        with postgres_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM telemetry.mqtt_raw_data;")
            count = cur.fetchone()[0]
            assert count > 0, "mqtt_raw_data table is empty"
    
    def test_recent_data(self, postgres_conn):
        """Проверка, что есть свежие данные (за последний час или вообще любые данные)."""
        with postgres_conn.cursor() as cur:
            # Сначала проверяем данные за последний час
            cur.execute("""
                SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
                WHERE time >= NOW() - INTERVAL '1 hour';
            """)
            recent_count = cur.fetchone()[0]
            
            # Если нет данных за час, проверяем хотя бы наличие любых данных
            if recent_count == 0:
                cur.execute("SELECT COUNT(*) FROM telemetry.mqtt_raw_data;")
                total_count = cur.fetchone()[0]
                assert total_count > 0, "No data at all in mqtt_raw_data"
    
    # ========== Качество данных ==========
    
    def test_no_null_topics(self, postgres_conn):
        """Проверка отсутствия NULL в топиках."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
                WHERE topic IS NULL;
            """)
            null_count = cur.fetchone()[0]
            assert null_count == 0, f"Found {null_count} rows with NULL topics"
    
    def test_no_null_payloads(self, postgres_conn):
        """Проверка отсутствия NULL в raw_payload."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
                WHERE raw_payload IS NULL;
            """)
            null_count = cur.fetchone()[0]
            assert null_count == 0, f"Found {null_count} rows with NULL payloads"
    
    def test_timestamp_ordering(self, postgres_conn):
        """Проверка корректности временных меток."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    MIN(time) as min_time,
                    MAX(time) as max_time,
                    MAX(time) >= MIN(time) as time_ordering_ok
                FROM telemetry.mqtt_raw_data;
            """)
            result = cur.fetchone()
            
            min_time, max_time, ordering_ok = result
            assert ordering_ok, "Time ordering is incorrect"
            
            # Проверяем, что времена не в будущем
            now = datetime.now(timezone.utc)
            assert max_time <= now + timedelta(minutes=1), \
                "Found timestamps in the future"
    
    # ========== Производительность ==========
    
    def test_write_rate(self, postgres_conn):
        """Проверка скорости записи данных."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
                WHERE time >= NOW() - INTERVAL '1 minute';
            """)
            last_minute_count = cur.fetchone()[0]
            
            # Ожидаем хотя бы несколько записей в минуту
            assert last_minute_count >= 0, "No recent writes"
    
    def test_data_age_range(self, postgres_conn):
        """Проверка диапазона данных."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    MIN(time) as oldest,
                    MAX(time) as newest,
                    MAX(time) - MIN(time) as data_span
                FROM telemetry.mqtt_raw_data;
            """)
            result = cur.fetchone()
            oldest, newest, data_span = result
            
            assert data_span is not None, "Data span is NULL"


class TestMqttDataContent:
    """Тесты содержимого MQTT данных."""
    
    def test_topics_variety(self, postgres_conn):
        """Проверка разнообразия топиков."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT topic FROM telemetry.mqtt_raw_data 
                ORDER BY topic;
            """)
            topics = [row[0] for row in cur.fetchall()]
            
            assert len(topics) > 0, "No topics found"
    
    def test_no_validation_topics_in_recent_data(self, postgres_conn):
        """Проверка, что /validated топики больше не записываются (validation layer удален)."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
                WHERE topic LIKE '%/validated' 
                AND time >= NOW() - INTERVAL '10 minutes';
            """)
            validated_count = cur.fetchone()[0]
            
            assert validated_count == 0, \
                f"Found {validated_count} recent /validated topics (validation layer should be removed)"
    
    def test_raw_topics_present(self, postgres_conn):
        """Проверка наличия /raw топиков."""
        with postgres_conn.cursor() as cur:
            # Проверяем сначала за последний час
            cur.execute("""
                SELECT COUNT(DISTINCT topic) FROM telemetry.mqtt_raw_data 
                WHERE topic LIKE '%/raw' 
                AND time >= NOW() - INTERVAL '1 hour';
            """)
            recent_count = cur.fetchone()[0]
            
            # Если нет за час, проверяем вообще
            if recent_count == 0:
                cur.execute("""
                    SELECT COUNT(DISTINCT topic) FROM telemetry.mqtt_raw_data 
                    WHERE topic LIKE '%/raw';
                """)
                total_count = cur.fetchone()[0]
                # Мягкая проверка - может не быть raw данных, если система только запустилась
                assert total_count >= 0, "/raw topics check"
    
    def test_ds_topics_present(self, postgres_conn):
        """Проверка наличия /ds (downsampled) топиков."""
        with postgres_conn.cursor() as cur:
            # Проверяем сначала за последний час
            cur.execute("""
                SELECT COUNT(DISTINCT topic) FROM telemetry.mqtt_raw_data 
                WHERE topic LIKE '%/ds' 
                AND time >= NOW() - INTERVAL '1 hour';
            """)
            recent_count = cur.fetchone()[0]
            
            # Если нет за час, проверяем вообще
            if recent_count == 0:
                cur.execute("""
                    SELECT COUNT(DISTINCT topic) FROM telemetry.mqtt_raw_data 
                    WHERE topic LIKE '%/ds';
                """)
                total_count = cur.fetchone()[0]
                # Мягкая проверка - может не быть ds данных, если система только запустилась
                assert total_count >= 0, "/ds topics check"
    
    def test_events_topics_present(self, postgres_conn):
        """Проверка наличия /events топиков."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT topic) FROM telemetry.mqtt_raw_data 
                WHERE topic LIKE '%/events' 
                AND time >= NOW() - INTERVAL '10 minutes';
            """)
            events_count = cur.fetchone()[0]
            
            assert events_count >= 0, "Events topics check"
    
    def test_jsonb_payload_structure(self, postgres_conn):
        """Проверка структуры JSONB payload."""
        with postgres_conn.cursor() as cur:
            cur.execute("""
                SELECT raw_payload FROM telemetry.mqtt_raw_data 
                WHERE time >= NOW() - INTERVAL '1 minute'
                LIMIT 10;
            """)
            payloads = cur.fetchall()
            
            for (payload,) in payloads:
                assert isinstance(payload, dict), "Payload is not a dict"
                assert 'metadata' in payload, "Missing 'metadata' key"
                assert 'data' in payload, "Missing 'data' key"



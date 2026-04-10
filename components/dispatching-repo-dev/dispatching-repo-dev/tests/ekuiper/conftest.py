"""
Pytest fixtures для Docker окружения.
"""
import pytest
import psycopg2
import paho.mqtt.client as mqtt
import json
import time
import os


@pytest.fixture(scope="session")
def test_config():
    """Конфигурация для Docker окружения."""
    return {
        # Docker service names из docker-compose
        'ekuiper_host': 'dispatching-ekuiper',
        'ekuiper_port': '9081',
        'postgres_host': 'dispatching-postgres',
        'postgres_port': '5432',
        'postgres_user': 'postgres',
        'postgres_password': 'postgres',
        'postgres_db': 'dispatching',
        'mqtt_host': 'dispatching-nanomq',
        'mqtt_port': 1883,
        'vehicle_id': os.getenv('VEHICLE_ID', '4')
    }


@pytest.fixture(scope="session")
def ekuiper_api(test_config) -> str:
    """URL для eKuiper REST API."""
    return f"http://{test_config['ekuiper_host']}:{test_config['ekuiper_port']}"


@pytest.fixture(scope="session")
def postgres_conn(test_config):
    """
    Подключение к PostgreSQL.
    
    ⚠️  autocommit=True потому что eKuiper пишет через своё подключение!
    Очистка данных происходит через cleanup_test_data fixture.
    """
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=test_config['postgres_host'],
                port=test_config['postgres_port'],
                user=test_config['postgres_user'],
                password=test_config['postgres_password'],
                dbname=test_config['postgres_db']
            )
            conn.autocommit = True
            yield conn
            conn.close()
            return
        except psycopg2.OperationalError:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise


@pytest.fixture
def postgres_cursor(postgres_conn):
    """Курсор для SQL запросов."""
    cursor = postgres_conn.cursor()
    yield cursor
    cursor.close()


@pytest.fixture(scope="session")
def mqtt_client(test_config):
    """MQTT клиент для публикации тестовых сообщений."""
    client = mqtt.Client(client_id="pytest-mqtt-client")
    
    connected = False
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
    
    client.on_connect = on_connect
    
    try:
        client.connect(
            test_config['mqtt_host'],
            test_config['mqtt_port'],
            keepalive=60
        )
        client.loop_start()
        
        # Ждем подключения
        timeout = 10
        start_time = time.time()
        while not connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not connected:
            raise RuntimeError(f"Failed to connect to MQTT broker")
        
        def publish_json(topic: str, payload: dict, qos: int = 0):
            """Публикация JSON сообщения."""
            json_payload = json.dumps(payload)
            result = client.publish(topic, json_payload, qos=qos)
            result.wait_for_publish()
            return result.is_published()
        
        client.publish_json = publish_json
        
        yield client
        
    finally:
        client.loop_stop()
        client.disconnect()


@pytest.fixture
def wait_for_processing():
    """Ожидание обработки данных."""
    def wait(seconds: int = 3):
        time.sleep(seconds)
    return wait


def pytest_addoption(parser):
    """Добавляем опции для запуска тестов."""
    parser.addoption(
        "--with-mocks",
        action="store_true",
        default=False,
        help="Публиковать моки данных перед запуском тестов"
    )
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Запускать E2E тесты (медленные, требуют ожидания записи в БД)"
    )


def pytest_configure(config):
    """Регистрируем custom markers."""
    config.addinivalue_line(
        "markers", "e2e: E2E тесты (медленные, требуют полной обработки данных)"
    )


def pytest_collection_modifyitems(config, items):
    """Пропускаем E2E тесты если не указан --run-e2e."""
    if config.getoption("--run-e2e"):
        # Запускаем все тесты
        return
    
    skip_e2e = pytest.mark.skip(reason="Пропущено: используй --run-e2e для запуска E2E тестов")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session")
def with_mocks(request):
    """Флаг, указывающий нужно ли использовать моки."""
    return request.config.getoption("--with-mocks")


@pytest.fixture(scope="session", autouse=True)
def setup_mock_data(request, mqtt_client, test_config, with_mocks):
    """
    Автоматически публикует моки данных если запущено с --with-mocks.
    
    Использование:
        pytest --with-mocks  # Публикует моки перед всеми тестами
        pytest               # Использует реальные данные
    """
    if not with_mocks:
        # Без моков - используем реальные данные
        yield
        return
    
    print("\n" + "="*80)
    print("🎭 РЕЖИМ С МОКАМИ: Публикуем тестовые данные...")
    print("="*80)
    
    vehicle_id = test_config['vehicle_id']
    timestamp = int(time.time())
    
    # Публикуем минимальный набор данных для всех датчиков
    mock_messages = [
        # GPS данные
        {
            'topic': f'truck/{vehicle_id}/gps',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp},
                'data': {'lat': 58.170120, 'lon': 59.829150}
            }
        },
        {
            'topic': f'truck/{vehicle_id}/gps',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp + 1},
                'data': {'lat': 58.170130, 'lon': 59.829160}
            }
        },
        # Speed данные
        {
            'topic': f'truck/{vehicle_id}/speed',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp},
                'data': {'speed': 30.0}
            }
        },
        {
            'topic': f'truck/{vehicle_id}/speed',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp + 1},
                'data': {'speed': 0.0}
            }
        },
        # Weight данные
        {
            'topic': f'truck/{vehicle_id}/weight',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp},
                'data': {'weight': 150.0}
            }
        },
        {
            'topic': f'truck/{vehicle_id}/weight',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp + 1},
                'data': {'weight': 0.0}
            }
        },
        {
            'topic': f'truck/{vehicle_id}/weight',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp + 2},
                'data': {'weight': 153.0}  # Вибрация
            }
        },
        # Fuel данные
        {
            'topic': f'truck/{vehicle_id}/fuel',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp},
                'data': {'fuel': 75.5}
            }
        },
        {
            'topic': f'truck/{vehicle_id}/fuel',
            'payload': {
                'metadata': {'bort': 'MOCK_TRUCK', 'timestamp': timestamp + 1},
                'data': {'fuel': 8.0}  # Низкий уровень для fuel alert
            }
        },
    ]
    
    # Публикуем все моки
    for i, msg in enumerate(mock_messages):
        result = mqtt_client.publish_json(msg['topic'], msg['payload'])
        if result:
            print(f"  ✅ [{i+1}/{len(mock_messages)}] Published to {msg['topic']}")
        else:
            print(f"  ❌ [{i+1}/{len(mock_messages)}] Failed to publish to {msg['topic']}")
        time.sleep(0.2)
    
    print("\n⏳ Ожидание обработки данных (10 секунд)...")
    time.sleep(10)
    
    print("✅ Моки данных опубликованы и обработаны")
    print("="*80 + "\n")
    
    yield
    
    print("\n🧹 Тесты с моками завершены")


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(request, test_config):
    """
    Автоматическая очистка тестовых данных после завершения всех тестов.
    
    Очищает:
    - Данные с bort='TEST_BORT', 'MOCK_TRUCK', 'DEBUG_TEST', etc.
    - Данные с test_id в metadata
    """
    yield  # Выполняются все тесты
    
    print("\n" + "="*80)
    print("🧹 CLEANUP: Removing test data...")
    print("="*80)
    
    try:
        # Создаём новое подключение для очистки
        conn = psycopg2.connect(
            host=test_config['postgres_host'],
            port=test_config['postgres_port'],
            user=test_config['postgres_user'],
            password=test_config['postgres_password'],
            dbname=test_config['postgres_db']
        )
        conn.autocommit = True
        
        cur = conn.cursor()
        
        # Подсчитываем тестовые данные
        cur.execute("""
            SELECT COUNT(*) FROM telemetry.mqtt_raw_data 
            WHERE raw_payload->'metadata'->>'bort' IN (
                'TEST_BORT', 'MOCK_TRUCK', 'DEBUG_TEST', 'LONG_WAIT_TEST'
            )
            OR raw_payload->'metadata' ? 'test_id';
        """)
        test_data_count = cur.fetchone()[0]
        
        if test_data_count > 0:
            # Удаляем тестовые данные
            cur.execute("""
                DELETE FROM telemetry.mqtt_raw_data 
                WHERE raw_payload->'metadata'->>'bort' IN (
                    'TEST_BORT', 'MOCK_TRUCK', 'DEBUG_TEST', 'LONG_WAIT_TEST'
                )
                OR raw_payload->'metadata' ? 'test_id';
            """)
            print(f"   ✅ Deleted {test_data_count} test records")
        else:
            print("   ℹ️  No test data found (clean)")
        
        # Статистика после очистки
        cur.execute("SELECT COUNT(*) FROM telemetry.mqtt_raw_data;")
        remaining_count = cur.fetchone()[0]
        print(f"   📊 Remaining records in DB: {remaining_count}")
        
        cur.close()
        conn.close()
            
    except Exception as e:
        print(f"   ⚠️  Cleanup error: {e}")
    
    print("="*80 + "\n")


@pytest.fixture
def sample_mqtt_messages(test_config):
    """Примеры MQTT сообщений для тестов."""
    timestamp = int(time.time())
    vehicle_id = test_config['vehicle_id']
    
    return {
        'gps': {
            'topic': f'truck/{vehicle_id}/gps',
            'payload': {
                'metadata': {'bort': 'АС26', 'timestamp': timestamp},
                'data': {'lat': 58.170120, 'lon': 59.829150}
            }
        },
        'speed': {
            'topic': f'truck/{vehicle_id}/speed',
            'payload': {
                'metadata': {'bort': 'АС26', 'timestamp': timestamp},
                'data': {'speed': 25.5}
            }
        },
        'weight': {
            'topic': f'truck/{vehicle_id}/weight',
            'payload': {
                'metadata': {'bort': 'АС26', 'timestamp': timestamp},
                'data': {'weight': 150.0}
            }
        },
        'fuel': {
            'topic': f'truck/{vehicle_id}/fuel',
            'payload': {
                'metadata': {'bort': 'АС26', 'timestamp': timestamp},
                'data': {'fuel': 75.5}
            }
        }
    }


@pytest.fixture
def mock_test_scenarios(test_config):
    """Моки данных для различных тестовых сценариев."""
    timestamp = int(time.time())
    vehicle_id = test_config['vehicle_id']
    
    return {
        # Сценарий 1: Нормальная работа
        'normal_operation': [
            {
                'topic': f'truck/{vehicle_id}/gps',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'lat': 58.17, 'lon': 59.83}}
            },
            {
                'topic': f'truck/{vehicle_id}/speed',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 1}, 'data': {'speed': 30.0}}
            },
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 2}, 'data': {'weight': 100.0}}
            }
        ],
        
        # Сценарий 2: Пустой грузовик
        'empty_truck': [
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'weight': 0.0}}
            }
        ],
        
        # Сценарий 3: Загруженный грузовик
        'loaded_truck': [
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'weight': 200.0}}
            }
        ],
        
        # Сценарий 4: Вибрация (резкое изменение веса)
        'vibration': [
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'weight': 100.0}}
            },
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 1}, 'data': {'weight': 103.0}}
            },
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 2}, 'data': {'weight': 99.0}}
            }
        ],
        
        # Сценарий 5: Превышение скорости
        'speeding': [
            {
                'topic': f'truck/{vehicle_id}/speed',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'speed': 75.0}}
            }
        ],
        
        # Сценарий 6: Низкий уровень топлива
        'low_fuel': [
            {
                'topic': f'truck/{vehicle_id}/fuel',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'fuel': 5.0}}
            }
        ],
        
        # Сценарий 7: Граничные значения
        'edge_cases': [
            {
                'topic': f'truck/{vehicle_id}/speed',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp}, 'data': {'speed': 0.0}}
            },
            {
                'topic': f'truck/{vehicle_id}/fuel',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 1}, 'data': {'fuel': 100.0}}
            },
            {
                'topic': f'truck/{vehicle_id}/weight',
                'payload': {'metadata': {'bort': 'АС26', 'timestamp': timestamp + 2}, 'data': {'weight': 250.0}}
            }
        ]
    }

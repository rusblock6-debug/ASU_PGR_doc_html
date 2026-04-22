#!/usr/bin/env python3
"""
Компактный TUI Event Visualizer для датчиков грузовика
Визуализирует состояния датчиков в режиме реального времени в терминале с ASCII графиками
"""

import json
import time
from datetime import datetime
from collections import deque, defaultdict
import threading
import paho.mqtt.client as mqtt
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
import asciichartpy

# Конфигурация
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
VEHICLE_ID = "4_truck"

# Топики для событий
EVENT_TOPICS = {
    "speed": f"truck/{VEHICLE_ID}/sensor/speed/events",
    "weight": f"truck/{VEHICLE_ID}/sensor/weight/events",
    "vibro": f"truck/{VEHICLE_ID}/sensor/vibro/events",
    "fuel": f"truck/{VEHICLE_ID}/sensor/fuel/alerts"
}

# Топики для downsampled значений
DS_TOPICS = {
    "speed": f"truck/{VEHICLE_ID}/sensor/speed/ds",
    "weight": f"truck/{VEHICLE_ID}/sensor/weight/ds",
    "fuel": f"truck/{VEHICLE_ID}/sensor/fuel/ds"
}

# Маппинг статусов
STATUS_MAPPING = {
    "speed": {"moving": "🟢", "stopped": "🔴"},
    "weight": {"loaded": "🟢", "empty": "🔴"},
    "vibro": {"active": "🟢", None: "🔴", "null": "🔴"},
    "fuel": {"alert_level": "🟠"}
}

# История событий (последние N точек для графика)
MAX_GRAPH_POINTS = 80  # 80 точек для графика событий (как и для значений)
sensor_history = {
    sensor: deque(maxlen=MAX_GRAPH_POINTS) 
    for sensor in EVENT_TOPICS.keys()
}

# История реальных значений из DS топиков (для графиков значений)
MAX_VALUE_POINTS = 80  # 80 точек для графиков значений
value_history = {
    "speed": deque(maxlen=MAX_VALUE_POINTS),
    "weight": deque(maxlen=MAX_VALUE_POINTS)
}

# Текущие значения датчиков
current_status = {
    "speed": {"status": "unknown", "value": None, "timestamp": None},
    "weight": {"status": "unknown", "value": None, "timestamp": None},
    "vibro": {"status": "unknown", "value": None, "timestamp": None},
    "fuel": {"status": "unknown", "value": None, "timestamp": None}
}

# Счетчики сообщений
message_counters = {
    "speed": 0,
    "weight": 0,
    "vibro": 0,
    "fuel": 0
}

# Блокировка для потокобезопасности
data_lock = threading.Lock()
mqtt_connected = False
total_messages = 0


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback при подключении к MQTT"""
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        # Подписываемся на event топики
        for sensor, topic in EVENT_TOPICS.items():
            client.subscribe(topic)
        # Подписываемся на DS топики
        for sensor, topic in DS_TOPICS.items():
            client.subscribe(topic)


def on_message(client, userdata, msg):
    """Callback при получении сообщения"""
    global total_messages
    try:
        payload = json.loads(msg.payload.decode())
        timestamp = time.time()
        data = payload.get("data", {})
        
        # Проверяем тип топика
        is_event = False
        is_ds = False
        sensor_type = None
        
        for sensor, topic in EVENT_TOPICS.items():
            if msg.topic == topic:
                is_event = True
                sensor_type = sensor
                break
        
        if not is_event:
            for sensor, topic in DS_TOPICS.items():
                if msg.topic == topic:
                    is_ds = True
                    sensor_type = sensor
                    break
        
        if not sensor_type:
            return
        
        with data_lock:
            total_messages += 1
            
            # Обработка event топиков
            if is_event:
                status = data.get("status")
                message_counters[sensor_type] += 1
                
                # Определяем бинарное значение
                mapping = STATUS_MAPPING.get(sensor_type, {})
                # Для графика: 1 = ON, 0 = OFF
                if sensor_type == "speed":
                    binary_value = 1 if status == "moving" else 0
                elif sensor_type == "weight":
                    binary_value = 1 if status == "loaded" else 0
                elif sensor_type == "vibro":
                    binary_value = 1 if status == "active" else 0
                elif sensor_type == "fuel":
                    binary_value = 1 if status == "alert_level" else 0
                else:
                    binary_value = 0
                
                # Обновляем текущий статус
                current_status[sensor_type]["status"] = status
                current_status[sensor_type]["timestamp"] = timestamp
                
                # Добавляем в историю для графика
                sensor_history[sensor_type].append({
                    "timestamp": timestamp,
                    "value": binary_value,
                    "status": status
                })
            
            # Обработка DS топиков
            elif is_ds:
                if sensor_type == "speed":
                    value = data.get("speed", 0)
                elif sensor_type == "weight":
                    value = data.get("weight", 0)
                elif sensor_type == "fuel":
                    value = data.get("fuel", 0)
                else:
                    return
                
                current_status[sensor_type]["value"] = value
                
                # Добавляем в историю значений для графика (только speed и weight)
                if sensor_type in ["speed", "weight"]:
                    value_history[sensor_type].append({
                        "timestamp": timestamp,
                        "value": value
                    })
                    # Логируем каждое добавленное значение
                    print(f"📊 {sensor_type}_ds: {value:.1f} @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]} | History size: {len(value_history[sensor_type])}")
        
    except Exception as e:
        pass  # Игнорируем ошибки парсинга


def create_header() -> Panel:
    """Создает заголовок приложения"""
    connection_status = "🟢 Connected" if mqtt_connected else "🔴 Disconnected"
    
    header_text = Text()
    header_text.append("🚛 Real-time Sensor Monitor", style="bold cyan")
    header_text.append(f" | Vehicle: {VEHICLE_ID}", style="bold yellow")
    header_text.append(f" | {connection_status}", style="bold")
    header_text.append(f" | Messages: {total_messages}", style="bold green")
    header_text.append(f" | {datetime.now().strftime('%H:%M:%S')}", style="bold white")
    
    return Panel(header_text, box=box.ROUNDED, style="cyan")


def create_value_graph(sensor_name: str, width: int = 80, height: int = 6) -> str:
    """Создает ASCII график реальных значений (speed/weight) из DS топиков"""
    with data_lock:
        history = list(value_history.get(sensor_name, []))
    
    current_time = time.time()
    
    if not history:
        # Пустой график
        empty_data = [0] * width
        graph = asciichartpy.plot(
            empty_data,
            {'height': height}
        )
        return graph + "\nNo data yet"
    
    # Получаем значения
    values = [point["value"] for point in history]
    timestamps = [point["timestamp"] for point in history]
    
    # Масштабируем к нужной ширине
    if len(values) < width:
        # Если данных меньше чем ширина, дополняем нулями слева
        scaled_values = [0] * (width - len(values)) + values
    else:
        # Если данных больше, берём последние width точек
        scaled_values = values[-width:]
    
    # Определяем диапазон для автоматического масштабирования
    # Минимум всегда 0, максимум - максимальное значение + 10% запаса
    min_val = 0
    if scaled_values and max(scaled_values) > 0:
        max_val = max(scaled_values) * 1.1  # Добавляем 10% запаса сверху
    else:
        max_val = 100  # Дефолтное значение для пустого графика
    
    # Создаём график
    graph = asciichartpy.plot(
        scaled_values,
        {
            'height': height,
            'min': min_val,
            'max': max_val,
            'format': '{:6.1f}'  # Формат: одна десятичная
        }
    )
    
    # Добавляем временные метки
    oldest_time = timestamps[0] if len(timestamps) == len(values) else current_time - 60
    oldest_dt = datetime.fromtimestamp(oldest_time)
    newest_dt = datetime.fromtimestamp(current_time)
    
    time_label_left = oldest_dt.strftime("%H:%M:%S")
    time_label_right = newest_dt.strftime("%H:%M:%S")
    
    # Статистика по всем значениям (не scaled, а оригинальным)
    if values:
        min_value = min(values)
        max_value = max(values)
        avg_value = sum(values) / len(values)
        stats = f"Min: {min_value:.1f} | Avg: {avg_value:.1f} | Max: {max_value:.1f}"
    else:
        stats = "No data"
    
    # Добавляем текущее значение и единицы измерения
    current_val = scaled_values[-1] if scaled_values else 0
    if sensor_name == "speed":
        unit = f"Now: {current_val:.1f} km/h"
    elif sensor_name == "weight":
        unit = f"Now: {current_val:.1f} t"
    else:
        unit = f"Now: {current_val:.1f}"
    
    # Форматируем метки: время слева | статистика в центре | текущее значение и время справа
    time_line = f"{time_label_left} | {stats} | {unit} | {time_label_right}"
    
    return graph + "\n" + time_line


def create_value_panel(sensor_name: str) -> Panel:
    """Создает панель с графиком реальных значений"""
    with data_lock:
        current_value = current_status[sensor_name]["value"]
    
    # Заголовок с единицами измерения и текущим значением
    if sensor_name == "speed":
        if current_value is not None:
            title = f"Speed Values: {current_value:.1f} km/h"
        else:
            title = "Speed Values (km/h)"
        color = "green"
    elif sensor_name == "weight":
        if current_value is not None:
            title = f"Weight Values: {current_value:.1f} t"
        else:
            title = "Weight Values (tons)"
        color = "blue"
    else:
        title = f"{sensor_name.capitalize()} Values"
        color = "cyan"
    
    # Создаем график
    graph = create_value_graph(sensor_name, width=80, height=6)
    
    # Создаем панель
    return Panel(
        graph,
        title=f"[bold {color}]{title}[/bold {color}]",
        border_style=color if mqtt_connected else "dim",
        expand=True
    )


def create_ascii_graph(sensor_name: str, width: int = 80, height: int = 6) -> str:
    """Создает ASCII график для датчика используя asciichartpy"""
    with data_lock:
        history = list(sensor_history[sensor_name])
    
    current_time = time.time()
    
    if not history:
        # Пустой график - показываем линию на уровне 0
        empty_data = [0.0] * width
        graph = asciichartpy.plot(
            empty_data,
            {'height': height, 'min': 0.0, 'max': 1.0, 'format': '{:1.0f}'}
        )
        # Добавляем отступ 4 пробела для выравнивания
        graph_lines = [f"    {line}" for line in graph.split('\n')]
        return '\n'.join(graph_lines) + "\n    No data yet"
    
    # Получаем значения (преобразуем в float для лучшей отрисовки)
    values = [float(point["value"]) for point in history]
    timestamps = [point["timestamp"] for point in history]
    
    # Масштабируем к нужной ширине
    if len(values) < width:
        # Если данных меньше чем ширина, запоминаем сколько пустых слева
        num_empty = width - len(values)
        # Дополняем NaN слева (для отсутствующих данных)
        scaled_values = [float('nan')] * num_empty + values
    else:
        # Если данных больше, берём последние width точек
        scaled_values = values[-width:]
        num_empty = 0
    
    # Добавляем небольшое смещение к нулевым значениям для видимости линии
    # NaN оставляем как NaN (пустые данные), 0 заменяем на 0.01 (реальные OFF события)
    display_values = []
    for i, v in enumerate(scaled_values):
        if i < num_empty or (not isinstance(v, float) or v != v):  # NaN check
            display_values.append(float('nan'))  # Пустые данные
        elif v > 0:
            display_values.append(v)  # Реальная единица
        else:
            display_values.append(0.01)  # Реальный ноль (OFF событие)
    
    # Создаём график с фиксированным диапазоном 0-1
    graph = asciichartpy.plot(
        display_values,
        {
            'height': height,
            'min': 0.0,         # Фиксированный минимум
            'max': 1.0,         # Фиксированный максимум
            'format': '{:1.0f}' # Формат меток: 0 и 1
        }
    )
    
    # Добавляем отступ 4 пробела для каждой строки графика
    graph_lines = [f"    {line}" for line in graph.split('\n')]
    
    # Добавляем временные метки
    oldest_time = timestamps[0] if len(timestamps) == len(values) else current_time - 60
    oldest_dt = datetime.fromtimestamp(oldest_time)
    newest_dt = datetime.fromtimestamp(current_time)
    
    time_label_left = oldest_dt.strftime("%H:%M:%S")
    time_label_right = newest_dt.strftime("%H:%M:%S")
    
    # Форматируем временные метки с отступом
    padding = width - len(time_label_left) - len(time_label_right)
    if padding < 0:
        padding = 1
    time_line = f"    {time_label_left}" + " " * padding + f"{time_label_right}"
    
    return '\n'.join(graph_lines) + "\n" + time_line


def create_sensor_panel(sensor_name: str) -> Panel:
    """Создает панель для конкретного датчика с графиком"""
    with data_lock:
        status_data = current_status[sensor_name]
        status = status_data["status"]
        value = status_data["value"]
        timestamp = status_data["timestamp"]
        count = message_counters[sensor_name]
    
    # Определяем иконку статуса
    status_icon = STATUS_MAPPING.get(sensor_name, {}).get(status, "⚪")
    
    # Форматируем значение
    value_str = "N/A"
    if value is not None:
        if sensor_name == "speed":
            value_str = f"{value:.1f} km/h"
        elif sensor_name == "weight":
            value_str = f"{value:.1f} t"
        elif sensor_name == "fuel":
            value_str = f"{value:.1f} L"
    
    # Форматируем время
    time_str = "N/A"
    if timestamp:
        elapsed = time.time() - timestamp
        if elapsed < 60:
            time_str = f"{int(elapsed)}s ago"
        else:
            time_str = f"{int(elapsed//60)}m ago"
    
    # Стиль для статуса
    if status == "moving" or status == "loaded" or status == "active":
        status_style = "bold green"
    elif status == "alert_level":
        status_style = "bold yellow"
    else:
        status_style = "dim"
    
    # Создаем компактную информацию вместо таблицы
    info = Text()
    info.append("Status: ", style="dim")
    info.append(f"{status_icon} {status}", style=status_style)
    info.append("  |  ", style="dim")
    info.append("Value: ", style="dim")
    info.append(value_str, style="bold")
    info.append("  |  ", style="dim")
    info.append("Events: ", style="dim")
    info.append(f"{count}", style="bold")
    info.append("  |  ", style="dim")
    info.append("Updated: ", style="dim")
    info.append(time_str, style="bold")
    
    # Создаем ASCII график (меньшая высота для событий)
    graph = create_ascii_graph(sensor_name, width=80, height=4)
    
    # Собираем содержимое панели (graph уже строка)
    content = Text()
    content.append_text(info)
    content.append("\n\n")
    content.append(graph)
    content.append("\n")  # Дополнительный отступ снизу для сохранения размера блока
    
    # Создаем панель с заголовком
    if sensor_name == "speed":
        sensor_title = "Speed Events"
    elif sensor_name == "weight":
        sensor_title = "Weight Events"
    elif sensor_name == "vibro":
        sensor_title = "Vibro Events"
    elif sensor_name == "fuel":
        sensor_title = "Fuel Events"
    else:
        sensor_title = f"{sensor_name.capitalize()} Events"
    
    return Panel(
        content,
        title=f"[bold cyan]{sensor_title}[/bold cyan]",
        border_style="cyan" if mqtt_connected else "dim",
        expand=True
    )


def create_layout() -> Layout:
    """Создает основной layout приложения - значения + статусы для speed и weight"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="speed_values", ratio=1),    # График значений скорости
        Layout(name="speed", ratio=1),            # График статусов скорости
        Layout(name="weight_values", ratio=1),    # График значений веса
        Layout(name="weight", ratio=1),           # График статусов веса
        Layout(name="vibro", ratio=1),            # График статусов вибрации
        # Layout(name="fuel", ratio=1),           # Скрыт
    )
    
    return layout


def update_display(layout: Layout):
    """Обновляет отображение данных"""
    # Обновляем заголовок
    layout["header"].update(create_header())
    
    # Обновляем графики значений (из DS топиков)
    layout["speed_values"].update(create_value_panel("speed"))
    layout["weight_values"].update(create_value_panel("weight"))
    
    # Обновляем графики статусов (из event топиков)
    layout["speed"].update(create_sensor_panel("speed"))
    layout["weight"].update(create_sensor_panel("weight"))
    layout["vibro"].update(create_sensor_panel("vibro"))
    # layout["fuel"].update(create_sensor_panel("fuel"))  # Скрыт


def main():
    """Главная функция"""
    console = Console()
    
    console.print()
    console.print("=" * 80, style="cyan")
    console.print("🚛 TUI Sensor Event Visualizer with ASCII Graphs", style="bold cyan", justify="center")
    console.print("=" * 80, style="cyan")
    console.print(f"MQTT Broker: [bold]{MQTT_BROKER}:{MQTT_PORT}[/bold]")
    console.print(f"Vehicle ID: [bold yellow]{VEHICLE_ID}[/bold yellow]")
    console.print(f"Graph history: [bold]{MAX_GRAPH_POINTS} points[/bold]")
    console.print("=" * 80, style="cyan")
    console.print()
    
    # Создаем MQTT клиент
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Подключаемся к брокеру
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        console.print(f"❌ Failed to connect to MQTT broker: {e}", style="bold red")
        return
    
    # Запускаем MQTT loop в отдельном потоке
    client.loop_start()
    
    # Ждем подключения
    console.print("⏳ Connecting to MQTT broker...", style="yellow")
    time.sleep(2)
    
    if not mqtt_connected:
        console.print("❌ Failed to connect to MQTT broker", style="bold red")
        client.loop_stop()
        return
    
    console.print("✅ Connected! Starting visualization...", style="bold green")
    console.print("Press [bold red]Ctrl+C[/bold red] to exit\n")
    time.sleep(1)
    
    # Создаем layout
    layout = create_layout()
    
    # Запускаем Live отображение
    try:
        with Live(layout, console=console, refresh_per_second=2, screen=True) as live:
            while True:
                update_display(layout)
                time.sleep(0.5)  # Обновляем каждые 0.5 секунды
                
    except KeyboardInterrupt:
        console.print("\n⚠️  Interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"\n❌ Visualization error: {e}", style="bold red")
    finally:
        client.loop_stop()
        client.disconnect()
        console.print("👋 Disconnected from MQTT broker", style="cyan")


if __name__ == "__main__":
    main()


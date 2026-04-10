#!/usr/bin/env python3
"""
Real-time Event Visualizer для датчиков грузовика
Визуализирует бинарные состояния датчиков в реальном времени
"""

import json
import time
from datetime import datetime
from collections import deque, defaultdict
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
import paho.mqtt.client as mqtt
import numpy as np

# Конфигурация
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
VEHICLE_ID = "4_truck"

# Топики для подписки (события)
TOPICS = {
    "speed": f"truck/{VEHICLE_ID}/sensor/speed/events",
    "weight": f"truck/{VEHICLE_ID}/sensor/weight/events",
    "vibro": f"truck/{VEHICLE_ID}/sensor/vibro/events",
    "fuel": f"truck/{VEHICLE_ID}/sensor/fuel/alerts"
}

# Топики для raw значений (downsampled)
DS_TOPICS = {
    "speed": f"truck/{VEHICLE_ID}/sensor/speed/ds",
    "weight": f"truck/{VEHICLE_ID}/sensor/weight/ds",
    "fuel": f"truck/{VEHICLE_ID}/sensor/fuel/ds"
}

# Маппинг статусов в бинарные значения
STATUS_MAPPING = {
    "speed": {"moving": 1, "stopped": 0},
    "weight": {"loaded": 1, "empty": 0},
    "vibro": {"active": 1, None: 0, "null": 0},
    "fuel": {"alert_level": 1}
}

# Цвета для датчиков
COLORS = {
    "speed": "#2ecc71",    # Зеленый
    "weight": "#3498db",   # Синий
    "vibro": "#e74c3c",    # Красный
    "fuel": "#f39c12"      # Оранжевый
}

# Хранилище данных (последние 60 секунд)
MAX_POINTS = 60
sensor_data = {
    sensor: deque(maxlen=MAX_POINTS) 
    for sensor in TOPICS.keys()
}

# Хранилище для истории downsampled значений (последние 60 секунд)
ds_data = {
    "speed": deque(maxlen=MAX_POINTS),
    "weight": deque(maxlen=MAX_POINTS)
}

# Хранилище для последних raw значений из /ds топиков
latest_ds_values = {
    "speed": None,
    "weight": None,
    "fuel": None
}

# Блокировка для потокобезопасности
import threading
data_lock = threading.Lock()


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback при подключении к MQTT"""
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        
        # Подписываемся на события
        for sensor, topic in TOPICS.items():
            client.subscribe(topic)
            print(f"📡 Subscribed to {topic}")
        
        # Подписываемся на downsampled данные
        for sensor, topic in DS_TOPICS.items():
            client.subscribe(topic)
            print(f"📡 Subscribed to {topic} (ds)")
    else:
        print(f"❌ Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback при получении сообщения"""
    try:
        payload = json.loads(msg.payload.decode())
        
        # ИСПОЛЬЗУЕМ ТЕКУЩЕЕ ВРЕМЯ для real-time графика
        timestamp = time.time()
        
        # Проверяем, это event или ds топик
        is_ds_topic = False
        for sensor, ds_topic in DS_TOPICS.items():
            if msg.topic == ds_topic:
                is_ds_topic = True
                data = payload.get("data", {})
                
                # Извлекаем значение
                if sensor == "speed":
                    value = data.get("speed")
                elif sensor == "weight":
                    value = data.get("weight")
                elif sensor == "fuel":
                    value = data.get("fuel")
                else:
                    value = None
                
                # Сохраняем в историю И последнее значение
                with data_lock:
                    if value is not None:
                        # Сохраняем историю только для speed и weight
                        if sensor in ds_data:
                            ds_data[sensor].append({
                                "timestamp": timestamp,
                                "value": value
                            })
                        latest_ds_values[sensor] = value
                
                print(f"📈 {sensor} (ds): {value} @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                return
        
        # Если не ds топик, обрабатываем как event
        if is_ds_topic:
            return
        
        data = payload.get("data", {})
        status = data.get("status")
        
        # Определяем тип датчика по топику
        sensor_type = None
        for sensor, topic in TOPICS.items():
            if msg.topic == topic:
                sensor_type = sensor
                break
        
        if not sensor_type:
            return
        
        # Маппим статус в бинарное значение
        mapping = STATUS_MAPPING.get(sensor_type, {})
        binary_value = mapping.get(status, 0)
        
        # Добавляем данные с текущим временем
        with data_lock:
            sensor_data[sensor_type].append({
                "timestamp": timestamp,
                "value": binary_value,
                "status": status
            })
        
        print(f"📊 {sensor_type}: {status} ({binary_value}) @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")


def init_plot():
    """Инициализация графика"""
    # 6 subplot'ов: speed_values, speed_events, weight_values, weight_events, vibro, fuel
    fig, axes = plt.subplots(6, 1, figsize=(14, 16), sharex=True)
    fig.suptitle(f'🚛 Real-time Sensor Data - Vehicle {VEHICLE_ID}', 
                 fontsize=16, fontweight='bold')
    
    # Конфигурация subplot'ов
    subplot_config = [
        ("Speed Values (km/h)", "speed", "values"),
        ("Speed Events", "speed", "events"),
        ("Weight Values (tons)", "weight", "values"),
        ("Weight Events", "weight", "events"),
        ("Vibro Events", "vibro", "events"),
        ("Fuel Alerts", "fuel", "events")
    ]
    
    for i, (ax, (title, sensor, plot_type)) in enumerate(zip(axes, subplot_config)):
        ax.set_ylabel(title, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_facecolor('#f8f9fa')
        
        if plot_type == "events":
            # Настройки для графиков событий
            ax.set_ylim(-0.2, 1.2)
            ax.set_yticks([0, 1])
            ax.set_yticklabels(['OFF', 'ON'])
            
            # Добавляем легенду статусов
            status_map = STATUS_MAPPING.get(sensor, {})
            legend_text = " | ".join([f"{k}={v}" for k, v in status_map.items()])
            ax.text(0.02, 0.95, legend_text, transform=ax.transAxes,
                    fontsize=8, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    axes[-1].set_xlabel('Time (seconds ago)', fontsize=12)
    plt.tight_layout()
    
    return fig, axes


def animate(frame, axes):
    """Обновление графика"""
    current_time = time.time()
    
    # Обновляем заголовок с текущим временем
    plt.gcf().suptitle(
        f'🚛 Real-time Sensor Data - Vehicle {VEHICLE_ID} | {datetime.now().strftime("%H:%M:%S")}',
        fontsize=16, fontweight='bold'
    )
    
    # Конфигурация subplot'ов (соответствует init_plot)
    subplot_config = [
        ("speed", "values", "km/h", 0),      # ax[0] - Speed Values
        ("speed", "events", None, 1),        # ax[1] - Speed Events
        ("weight", "values", "tons", 2),     # ax[2] - Weight Values
        ("weight", "events", None, 3),       # ax[3] - Weight Events
        ("vibro", "events", None, 4),        # ax[4] - Vibro Events
        ("fuel", "events", None, 5)          # ax[5] - Fuel Alerts
    ]
    
    with data_lock:
        for sensor, plot_type, unit, ax_idx in subplot_config:
            ax = axes[ax_idx]
            ax.clear()
            
            if plot_type == "values":
                # === ГРАФИК ЗНАЧЕНИЙ (линейный график) ===
                ax.set_ylabel(f"{sensor.capitalize()} ({unit})", fontsize=11, fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_facecolor('#f8f9fa')
                
                # Получаем данные downsampled значений
                data_points = list(ds_data[sensor])
                
                if data_points:
                    # Сортируем по времени
                    data_points.sort(key=lambda x: x['timestamp'])
                    
                    # Вычисляем относительное время (секунды назад)
                    times = [-(current_time - point['timestamp']) for point in data_points]
                    values = [point['value'] for point in data_points]
                    
                    # Рисуем линию
                    ax.plot(times, values, 
                           linewidth=2, 
                           color=COLORS[sensor], 
                           marker='o', 
                           markersize=3,
                           alpha=0.8)
                    
                    # Заливаем область под графиком
                    ax.fill_between(times, values, 
                                   alpha=0.2, 
                                   color=COLORS[sensor])
                    
                    # Показываем текущее значение
                    if values:
                        last_value = values[-1]
                        ax.text(0.98, 0.95, f"Now: {last_value:.1f} {unit}", 
                               transform=ax.transAxes,
                               fontsize=10, fontweight='bold',
                               horizontalalignment='right',
                               verticalalignment='top',
                               bbox=dict(boxstyle='round', 
                                        facecolor=COLORS[sensor],
                                        alpha=0.8,
                                        edgecolor='black',
                                        linewidth=2))
                    
                    # Автомасштабирование по Y с небольшим отступом
                    if values:
                        y_min, y_max = min(values), max(values)
                        y_range = y_max - y_min
                        if y_range > 0:
                            ax.set_ylim(y_min - y_range * 0.1, y_max + y_range * 0.1)
                        else:
                            ax.set_ylim(y_min - 1, y_max + 1)
                
            else:
                # === ГРАФИК СОБЫТИЙ (блоки состояний) ===
                title = f"{sensor.capitalize()} Events"
                ax.set_ylabel(title, fontsize=11, fontweight='bold')
                ax.set_ylim(-0.2, 1.2)
                ax.set_yticks([0, 1])
                ax.set_yticklabels(['OFF', 'ON'])
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_facecolor('#f8f9fa')
                
                # Легенда статусов
                status_map = STATUS_MAPPING.get(sensor, {})
                legend_text = " | ".join([f"{k}={v}" for k, v in status_map.items()])
                ax.text(0.02, 0.95, legend_text, transform=ax.transAxes,
                        fontsize=8, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                # Получаем данные событий
                data_points = list(sensor_data[sensor])
                
                if data_points:
                    # Сортируем по времени
                    data_points.sort(key=lambda x: x['timestamp'])
                    
                    # Рисуем горизонтальные блоки для каждого состояния
                    for j in range(len(data_points)):
                        point = data_points[j]
                        value = point['value']
                        
                        # Время начала блока (секунды назад, отрицательное)
                        x_start = -(current_time - point['timestamp'])
                        
                        # Время окончания блока
                        if j < len(data_points) - 1:
                            # Блок заканчивается при следующем событии
                            x_end = -(current_time - data_points[j + 1]['timestamp'])
                        else:
                            # Последний блок идет до текущего момента
                            x_end = 0
                        
                        # Ширина блока
                        width = x_end - x_start
                        
                        # Рисуем прямоугольник для состояния ON (value=1)
                        if value == 1 and width > 0:
                            rect = Rectangle(
                                (x_start, 0.1),  # Начальная позиция (x, y)
                                width,           # Ширина
                                0.8,             # Высота (от 0.1 до 0.9)
                                facecolor=COLORS[sensor],
                                edgecolor='darkgray',
                                linewidth=0.5,
                                alpha=0.7
                            )
                            ax.add_patch(rect)
                        
                        # Рисуем тонкий прямоугольник для состояния OFF (value=0)
                        elif value == 0 and width > 0:
                            rect = Rectangle(
                                (x_start, 0.45),  # Центрированная тонкая линия
                                width,
                                0.1,
                                facecolor='lightgray',
                                edgecolor='gray',
                                linewidth=0.5,
                                alpha=0.5
                            )
                            ax.add_patch(rect)
                    
                    # Показываем текущее состояние с raw значением
                    last_value = data_points[-1]['value']
                    last_status = data_points[-1].get('status', 'unknown')
                    
                    # Формируем текст с raw значением из ds топика
                    status_lines = [f"Now: {last_status}"]
                    
                    # Добавляем raw значение, если датчик имеет ds топик
                    if sensor in latest_ds_values:
                        ds_value = latest_ds_values[sensor]
                        if ds_value is not None:
                            if sensor == "speed":
                                status_lines.append(f"{ds_value:.1f} km/h")
                            elif sensor == "weight":
                                status_lines.append(f"{ds_value:.1f} tons")
                            elif sensor == "fuel":
                                status_lines.append(f"{ds_value:.1f} L")
                    
                    status_text = "\n".join(status_lines)
                    ax.text(0.98, 0.5, status_text, transform=ax.transAxes,
                           fontsize=10, fontweight='bold',
                           horizontalalignment='right',
                           verticalalignment='center',
                           bbox=dict(boxstyle='round', 
                                    facecolor=COLORS[sensor] if last_value == 1 else 'lightgray',
                                    alpha=0.8,
                                    edgecolor='black',
                                    linewidth=2))
            
            # Устанавливаем диапазон X (последние 60 секунд)
            ax.set_xlim(-MAX_POINTS, 0)
    
    # Общий xlabel только для нижнего графика
    axes[-1].set_xlabel('Time (seconds ago)', fontsize=12)


def main():
    """Главная функция"""
    print("=" * 60)
    print("🚛 Real-time Sensor Event Visualizer")
    print("=" * 60)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Vehicle ID: {VEHICLE_ID}")
    print(f"Max history: {MAX_POINTS} seconds")
    print("=" * 60)
    print()
    
    # Создаем MQTT клиент
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Подключаемся к брокеру
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"❌ Failed to connect to MQTT broker: {e}")
        return
    
    # Запускаем MQTT loop в отдельном потоке
    client.loop_start()
    
    # Ждем немного для получения первых данных
    print("⏳ Waiting for initial data...")
    time.sleep(2)
    
    # Создаем и запускаем визуализацию
    fig, axes = init_plot()
    
    # Анимация с обновлением каждые 500ms
    ani = animation.FuncAnimation(
        fig, animate, fargs=(axes,),
        interval=500,  # 500ms
        cache_frame_data=False
    )
    
    print("✅ Visualization started! Close the window to stop.")
    print()
    
    try:
        plt.show()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    finally:
        client.loop_stop()
        client.disconnect()
        print("👋 Disconnected from MQTT broker")


if __name__ == "__main__":
    main()


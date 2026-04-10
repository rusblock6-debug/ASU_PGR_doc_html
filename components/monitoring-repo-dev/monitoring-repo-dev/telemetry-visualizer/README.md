# Real-time Sensor Event Visualizer

Визуализация бинарных состояний датчиков грузовика в реальном времени через MQTT.

## 📦 Два режима визуализации

### 1. **GUI режим** (`visualizer.py`) - Matplotlib графики
- ✅ Графические step plots для каждого датчика
- ✅ История последних 60 секунд
- ✅ Цветовая индикация состояний
- ✅ Автоматическое обновление графиков

### 2. **TUI режим** (`visualizer_tui.py`) - Terminal UI
- ✅ Компактное отображение в терминале с ASCII графиками
- ✅ Горизонтальное размещение датчиков (2x2 сетка)
- ✅ История последних 60 точек на графике
- ✅ Счетчики событий и real-time обновления
- ✅ Минимальные требования к ресурсам
- ✅ Работает по SSH на удаленных серверах

## 🎯 Общие возможности

- ✅ Real-time визуализация 4 датчиков
- ✅ Бинарные состояния (ON/OFF)
- ✅ Автоматическая подписка на MQTT топики
- ✅ Интеграция с downsampled значениями

## 📊 Датчики

1. **Speed** (Скорость)
   - `moving` = ON (зеленый)
   - `stopped` = OFF

2. **Weight** (Вес)
   - `loaded` = ON (синий)
   - `empty` = OFF

3. **Vibro** (Вибрация)
   - `active` = ON (красный)
   - `null` = OFF

4. **Fuel** (Топливо)
   - `alert_level` = ON (оранжевый)
   - нет алерта = OFF

## 🚀 Установка

```bash
cd telemetry-visualizer

# Установка зависимостей
pip install -r requirements.txt
```

## 📱 Запуск

### GUI режим (Matplotlib)
```bash
python visualizer.py
```

### TUI режим (Terminal UI)
```bash
python visualizer_tui.py
```

> **Рекомендация**: Используй TUI режим для серверов без GUI или для мониторинга в терминале. GUI режим предоставляет более детальную визуализацию с графиками.

## ⚙️ Конфигурация

Отредактируйте `visualizer.py` или `visualizer_tui.py`:

```python
MQTT_BROKER = "localhost"  # Адрес MQTT брокера
MQTT_PORT = 1883           # Порт брокера
VEHICLE_ID = "4_truck"     # ID грузовика

# Только для GUI режима
MAX_POINTS = 60            # История (секунды)

# Только для TUI режима
MAX_GRAPH_POINTS = 60      # Кол-во точек на графике
```

## 📡 MQTT Топики

```
truck/4_truck/sensor/speed/events  → Speed events (moving/stopped)
truck/4_truck/sensor/weight/events → Weight events (loaded/empty)
truck/4_truck/sensor/vibro/events  → Vibro events (active/null)
truck/4_truck/sensor/fuel/alerts   → Fuel alerts (alert_level)

truck/4_truck/sensor/speed/ds      → Speed downsampled values
truck/4_truck/sensor/weight/ds     → Weight downsampled values
truck/4_truck/sensor/fuel/ds       → Fuel downsampled values
```

## 🎨 Визуализация

### TUI режим (Terminal UI)
```
╔════════════════════════════ Real-time Sensor Monitor ════════════════╗
║ 🚛 Vehicle: 4_truck | 🟢 Connected | Messages: 316 | 06:30:27       ║
╚══════════════════════════════════════════════════════════════════════╝

┌─────────────────── Speed ────────────────────┬─────────────────── Weight ────────────────────┐
│ Status:   🟢 moving                           │ Status:   🟢 loaded                            │
│ Value:    45.5 km/h                          │ Value:    85.3 t                               │
│ Events:   125                                │ Events:   87                                   │
│ Updated:  2s ago                             │ Updated:  5s ago                               │
│                                              │                                                │
│ 1 │████████████          ████████            │ 1 │              ████████████████              │
│   │████████████          ████████            │   │              ████████████████              │
│   │████████████          ████████            │   │              ████████████████              │
│   │████████████          ████████            │   │              ████████████████              │
│ 0 │████████████▁▁▁▁▁▁▁▁▁▁████████▁▁▁▁▁▁▁▁▁▁  │ 0 │▁▁▁▁▁▁▁▁▁▁▁▁▁▁████████████████              │
│   └──────────────────────────────────────    │   └────────────────────────────────────────   │
└──────────────────────────────────────────────┴────────────────────────────────────────────────┘

┌─────────────────── Vibro ────────────────────┬─────────────────── Fuel ──────────────────────┐
│ Status:   🟢 active                           │ Status:   ⚪ unknown                           │
│ Value:    N/A                                │ Value:    N/A                                  │
│ Events:   23                                 │ Events:   0                                    │
│ Updated:  1s ago                             │ Updated:  N/A                                  │
│                                              │                                                │
│ 1 │  █  █  █                                 │ 1 │                                            │
│   │  █  █  █                                 │   │                                            │
│   │  █  █  █                                 │   │                                            │
│   │  █  █  █                                 │   │                                            │
│ 0 │▁▁█▁▁█▁▁█▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁    │ 0 │▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁  │
│   └──────────────────────────────────────    │   └────────────────────────────────────────   │
└──────────────────────────────────────────────┴────────────────────────────────────────────────┘
```

**Особенности TUI режима:**
- 🎨 ASCII графики показывают историю состояний (60 точек)
- 📊 Горизонтальное размещение датчиков в сетке 2x2
- 🔴🟢 Цветные индикаторы статусов с эмодзи
- 📈 Real-time обновление каждые 0.5 секунды
- 💻 Работает в любом терминале (SSH, консоль)
- ▁ OFF состояние показано тонкой линией внизу
- █ ON состояние показано заполненными блоками

## 🔧 Требования

- Python 3.8+
- MQTT broker (Nanomq) на localhost:1883
- Running eKuiper с настроенными правилами событий

## 📝 Формат данных

### Event Messages (бинарные состояния)
```json
{
  "metadata": {
    "vehicle_id": "АС26",
    "sensor_type": "speed",
    "timestamp": 1759382219
  },
  "data": {
    "status": "moving",
    "speed": 45.5
  }
}
```

### Downsampled Messages (raw значения)
```json
{
  "metadata": {
    "bort": "АС26",
    "timestamp": 1759382219
  },
  "data": {
    "speed": 45.3,     // для speed/ds
    "weight": 125.7,   // для weight/ds
    "fuel": 850.2      // для fuel/ds
  }
}
```

## 🛠️ Troubleshooting

### Нет данных на графике
```bash
# Проверь MQTT брокер
docker ps | grep nanomq

# Проверь топики
mosquitto_sub -h localhost -p 1883 -t 'truck/4_truck/sensor/+/events' -v

# Проверь eKuiper правила
curl -s http://localhost:9081/rules | jq '.[] | {id, status}'
```

### Connection refused
```bash
# Проверь порт Nanomq
docker compose -f docker-compose.bort.yaml ps nanomq

# Проверь сетевые настройки
netstat -an | grep 1883
```

### TUI режим не отображается корректно
```bash
# Увеличь размер терминала до минимум 160x40
# Проверь поддержку UTF-8 в терминале
echo $LANG

# Установи правильную локаль
export LANG=en_US.UTF-8
```

## 📚 Зависимости

- `paho-mqtt==2.1.0` - MQTT клиент
- `matplotlib==3.9.0` - Визуализация (GUI режим)
- `numpy==1.26.4` - Числовые вычисления (GUI режим)
- `rich==13.7.0` - Terminal UI библиотека (TUI режим)
- `asciichartpy==1.5.25` - Компактные ASCII графики для TUI (TUI режим)

## 💡 Советы по использованию

### GUI режим лучше для:
- Детального анализа временных рядов
- Сохранения скриншотов графиков
- Презентаций и демонстраций
- Работы на локальном компьютере

### TUI режим лучше для:
- Мониторинга на удаленных серверах по SSH
- Работы в консольных окружениях без GUI
- Экономии ресурсов (CPU, память)
- Запуска в tmux/screen сессиях
- Встраивания в CI/CD пайплайны

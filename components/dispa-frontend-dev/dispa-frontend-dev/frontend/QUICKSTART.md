# Быстрый старт Frontend

## Запуск для разработки

### Вариант 1: Локальный запуск (рекомендуется для разработки)

```bash
cd /home/artem/projects/dispatching-repo/frontend

# Установить зависимости
npm install

# Запустить dev server
npm run dev
```

Приложение будет доступно на **http://localhost:5173**

**Преимущества:**
- ✅ Hot reload (мгновенное обновление при изменениях)
- ✅ Быстрый старт без Docker
- ✅ Удобная отладка в браузере

### Вариант 2: Запуск через Docker

```bash
cd /home/artem/projects/dispatching-repo

# Собрать и запустить frontend
docker compose -f docker-compose.bort.yaml up frontend --build
```

Приложение будет доступно на **http://localhost:3000**

## Проверка работоспособности

1. **Откройте в браузере:** http://localhost:5173 (или 3000 для Docker)

2. **Должны увидеть:**
   - Боковое меню слева с кнопками
   - Хедер с "Зарегистрированы на смене: admin"
   - Кнопку "Задания на смену"
   - Кнопку "Приступить к смене"
   - Кнопку "Назад"

3. **Нажмите "Задания на смену"** - должен загрузиться список заданий из Trip Service

## Требования

### Для локального запуска:
- Node.js 18+ (рекомендуется 18.x)
- npm 9+

### Для Docker:
- Docker 20+
- Docker Compose 2+

## Backend зависимости

**ВАЖНО:** Trip Service должен быть запущен на порту 8000

```bash
# В другом терминале запустите Trip Service
cd /home/artem/projects/dispatching-repo
docker compose -f docker-compose.bort.yaml up trip-service
```

Проверьте: http://localhost:8000/health

## Основные функции

### 1. Загрузка заданий

Кнопка **"Задания на смену"** → Загружает все задания через `GET /api/tasks`

### 2. Начало смены

Кнопка **"Приступить к смене"** → Активирует первое задание через `PUT /api/tasks/{id}`

### 3. Переключение заданий

**Клик на строку "Маршрут N"** → 
- Предыдущее активное → статус "Приостановлено"
- Выбранное → статус "В работе"

## Troubleshooting

### Ошибка "Cannot connect to Trip Service"

**Решение:** Убедитесь что Trip Service запущен:

```bash
docker compose -f docker-compose.bort.yaml up trip-service
curl http://localhost:8000/health
```

### Ошибка "Module not found"

**Решение:** Переустановите зависимости:

```bash
rm -rf node_modules package-lock.json
npm install
```

### Frontend не обновляется при изменениях

**Решение:** Перезапустите dev server:

```bash
# Ctrl+C чтобы остановить
npm run dev
```

## Разработка

### Горячая перезагрузка (Hot Reload)

Все изменения в файлах `.tsx`, `.ts`, `.css` автоматически применяются без перезапуска.

### Структура файлов для изменений

```
frontend/src/
├── pages/shift-tasks/
│   ├── ShiftTasksPage.tsx    # Главная страница (логика)
│   └── ShiftTasksPage.css    # Стили страницы
└── shared/api/
    └── tripServiceApi.ts     # API клиент (запросы к backend)
```

### Изменение стилей

Редактируйте `src/pages/shift-tasks/ShiftTasksPage.css`

Основные классы:
- `.task-row` - строка задания
- `.task-row-active` - активное задание
- `.start-shift-button` - кнопка "Приступить к смене"

### Изменение логики

Редактируйте `src/pages/shift-tasks/ShiftTasksPage.tsx`

Основные функции:
- `loadShiftTasks()` - загрузить задания
- `startShift()` - начать смену
- `handleTaskClick()` - клик по заданию

## Production Build

```bash
# Собрать production версию
npm run build

# Результат будет в dist/
ls -la dist/
```

## Дополнительная информация

- **README.md** - полная документация
- **API_SUMMARY.md** (в app/) - описание Trip Service API


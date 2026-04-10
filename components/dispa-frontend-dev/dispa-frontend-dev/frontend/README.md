# Frontend - Диспетчеризация горных работ

React приложение для отображения и управления заданиями на смену.

## Описание

Frontend сервис для отображения списка заданий на смену с возможностью:
- Просмотра всех заданий за текущую смену
- Активации первого задания кнопкой "Приступить к смене"
- Переключения между заданиями (клик по строке задания)
- Отображения статусов заданий (На выполнение, В работе, Выполнено, Приостановлено)

## Технологический стек

- **React 18.2** - UI библиотека
- **TypeScript 5.2** - типизация
- **Vite 5.0** - сборщик и dev server
- **Axios 1.6** - HTTP клиент
- **CSS Modules** - стилизация компонентов

## Установка и запуск

### Локальная разработка

```bash
# Установить зависимости
npm install

# Настроить окружение
cp .env.example .env
# Отредактировать .env с вашими настройками

# Запустить dev сервер
npm run dev
```

Приложение будет доступно на http://localhost:5173

### Docker разработка

```bash
# Собрать и запустить через docker-compose
docker compose up frontend --build
```

Приложение будет доступно на http://localhost:3000

## Структура проекта

```
frontend/
├── src/
│   ├── App.tsx                    # Главный компонент
│   ├── App.css                    # Глобальные стили
│   ├── main.tsx                   # Точка входа
│   ├── pages/                     # Страницы приложения
│   │   └── shift-tasks/           # Страница заданий на смену
│   │       ├── ShiftTasksPage.tsx # Компонент страницы
│   │       └── ShiftTasksPage.css # Стили страницы
│   └── shared/                    # Общие компоненты
│       └── api/                   # API клиенты
│           └── tripServiceApi.ts  # Trip Service API
├── index.html                     # HTML шаблон
├── package.json                   # Зависимости
├── vite.config.ts                 # Vite конфигурация
├── tsconfig.json                  # TypeScript конфигурация
├── Dockerfile                     # Docker образ
└── nginx.conf                     # Nginx конфигурация
```

## API интеграция

Приложение интегрируется с Trip Service API:

- `GET /api/tasks` - получить список заданий
- `GET /api/active/task` - получить активное задание
- `PUT /api/tasks/{id}` - обновить задание (смена статуса)
- `DELETE /api/active/task` - деактивировать задание

### Пример использования API

```typescript
import { tripServiceApi } from '@/shared/api/tripServiceApi';

// Загрузить задания
const tasks = await tripServiceApi.getTasks({ page: 1, size: 100 });

// Активировать задание
await tripServiceApi.activateTask('task-001');

// Приостановить задание
await tripServiceApi.pauseTask('task-001');
```

## Основные компоненты

### ShiftTasksPage

Главная страница приложения со списком заданий на смену.

**Функциональность:**
- Отображение списка заданий
- Кнопка "Задания на смену" - обновить список
- Кнопка "Приступить к смене" - активировать первое задание
- Клик по заданию - переключение активного задания
- Боковое меню навигации

**Состояния заданий:**
- `На выполнение` - pending
- `В работе` - active
- `Выполнено` - completed
- `Приостановлено` - paused

## Переменные окружения

```bash
# API Configuration
AUTH_API_URL=http://localhost:8001  # URL Auth Service API
VITE_API_URL=http://localhost:8000  # URL Trip Service API
VEHICLE_ID=4_truck                  # ID транспорта (передаётся как VITE_VEHICLE_ID)
```

## Разработка

### Запуск dev сервера

```bash
npm run dev
```

Dev сервер с hot reload будет доступен на http://localhost:5173

### Сборка production

```bash
npm run build
```

Собранное приложение будет в директории `dist/`

### Preview production build

```bash
npm run preview
```

## Docker deployment

### Сборка образа

```bash
docker build -t dispatching-frontend .
```

### Запуск контейнера

```bash
docker run -p 3000:80 dispatching-frontend
```

## Стилизация

Приложение использует CSS Modules для изоляции стилей компонентов.

**Основные цвета:**
- Зеленый (#7ba87b) - активные элементы, кнопки навигации
- Голубой (#76c7c0) - кнопка "Приступить к смене"
- Белый (#ffffff) - фон, карточки
- Серый (#f0f0f0) - боковое меню, неактивные элементы

## Будущие улучшения

- [ ] Добавить React Router для навигации между страницами
- [ ] Реализовать другие страницы (Настройки, Журнал событий, etc.)
- [ ] Добавить Redux для глобального state management
- [ ] Интегрировать WebSocket для real-time обновлений
- [ ] Добавить unit тесты (Vitest + Testing Library)
- [ ] Добавить авторизацию пользователей


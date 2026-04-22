# Bort Client

Клиентское приложение на React для бортовой части.

## Технологический стек

- React 19
- TypeScript
- Vite
- Mantine UI
- React Router
- PostCSS

## Требования

- Node.js: минимальная версия v22.14.0

## Конфигурация окружения

Приложение использует переменные окружения для указания API. Файл `.env` в корне проекта содержит дефолтные адреса API для докер контейнера при разворачивании всей системы локально через [управляющий репозиторий](https://git.dmi-msk.ru/retek.pgr/dispatching/dispatching-repo).
Чтобы переопределить под себя — создайте `.env.local` (он в `.gitignore`).

## Запуск

1. Установите зависимости:

```bash
npm install
```

2. Настройте переменные окружения (см. раздел «Конфигурация окружения»)

3. Запустите dev-сервер:

```bash
npm run dev
```

Приложение будет доступно по адресу http://localhost:5173.

Для запуска всех сервисов локально, выполнить в корне проекта [dispatching-repo](https://git.dmi-msk.ru/retek.pgr/dispatching/dispatching-repo):

```bash
docker compose -f docker-compose.server.yaml up -d --build && docker compose -f docker-compose.bort.yaml up -d --build
```

## ESLint Bulk Suppressions

### Что это такое?

**Bulk Suppressions** — система постепенного внедрения строгих правил ESLint. Позволяет использовать новые правила для свежего кода, а существующие нарушения «заморозить» в файле `eslint-suppressions.json`.
Подробнее [почитать можно тут](https://eslint.org/blog/2025/04/introducing-bulk-suppressions/) и [тут](https://eslint.org/docs/latest/use/suppressions).

### Основные команды

```bash
# Обычная проверка (видны только новые errors + warnings)
npm run lint

# Исправить проблемы в авто режиме (исправит не все)
npm run lint:fix

# Создать/обновить список для всех текущих ошибок
npm run lint:suppress-all

# Очистить неактуальные ошибки (использовать после исправления)
npm run lint:prune-suppressions

# Заглушить только конкретное правило
npx eslint . --suppress-rule no-console --fix
```

### Workflow

**При разработке:**

1. Пишите новый код — ESLint сразу покажет ошибки
2. Исправьте все **errors** (они блокируют коммит)
3. **Warnings** исправляйте по возможности

**При рефакторинге:**

1. Исправили старые нарушения (errors)? → `npm run lint:prune-suppressions`
2. Добавили новые строгие правила? → `npm run lint:suppress-all`

**Важно:**

- Файл `eslint-suppressions.json` **должен быть в git**. **Редактировать его вручную нельзя**! Изменения вносятся только с помощью команды:
  `npm run lint:prune-suppressions`.
- Если увидели предупреждение "suppressions left that do not occur anymore" → запустите `npm run lint:prune-suppressions`
- Если исправили ошибку, но не выполнили `npm run lint:prune-suppressions`, то гитлаб пайплайн будет падать с ошибкой
- Если pre-commit хук не позволяет закоммитить код: убедитесь, что все ошибки в файле, который вы хотите закоммитить, исправлены. Затем выполните команду: `npm run lint:prune-suppressions` и попробуйте закоммитить снова.

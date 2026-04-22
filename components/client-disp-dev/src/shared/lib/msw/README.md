# MSW Mocks

Mock Service Worker для эмуляции API в dev-режиме.
Позволяет эмулировать поведение бэкенда в ситуациях, когда по каким-то причинам невозможно использовать реальный бэкенд для полноценной разработки фронтенда, а также когда необходимо изолированно протестировать различные пользовательские сценарии.

## Быстрый старт

1. Создайте `.env` в корне проекта:

```bash
VITE_ENABLE_MSW=true
```

2. Запустите dev-сервер:

```bash
npm run dev
```

В консоли браузера появится `[MSW] Mocking enabled.`

## Структура

```
msw/
├── index.ts          # Публичный API
├── browser.ts        # Service Worker
├── config.ts         # Настройки (delay, кол-во данных)
├── handlers/         # HTTP-обработчики
│   ├── vehicles.ts
│   └── vehicle-models.ts
└── generators/       # Генераторы фейковых данных
    ├── vehicle.ts
    └── vehicle-model.ts
```

## Настройка

### Через config.ts

```ts
export const mswConfig = {
  delay: 300, // Задержка ответа (ms)
  paginatedListSize: 50, // Кол-во генерируемых элементов для списков с пагинацией/infinite scroll.
  dictionarySize: 20, // Кол-во генерируемых элементов для небольших справочников.
};
```

### Через localStorage (для отладки)

```js
localStorage.setItem('msw_delay', '1000'); // Задержка 1 сек
localStorage.setItem('msw_paginated_list_size', '100'); // 100 элементов
localStorage.setItem('msw_dictionary_size', '100'); // 100 элементов
```

## Добавление нового endpoint

1. Создайте генератор в `generators/`:

```ts
// generators/trip.ts
import { faker } from '@faker-js/faker';
import type { Trip } from '@/shared/api/endpoints/trips';

export function generateTrip(): Trip {
  return {
    id: faker.string.uuid(),
    // ...
  };
}
```

2. Создайте handler в `handlers/`:

```ts
// handlers/trips.ts
import { delay, http, HttpResponse } from 'msw';
import { generateTrips } from '../generators/trip';
import { mswConfig } from '../config';

export const tripsHandlers = [
  http.get('/api/trips', async () => {
    await delay(mswConfig.delay);
    return HttpResponse.json({ items: generateTrips(50) });
  }),
];
```

3. Добавьте в `handlers/index.ts`:

```ts
import { tripsHandlers } from './trips';

export const handlers = [
  ...vehiclesHandlers,
  ...vehicleModelsHandlers,
  ...tripsHandlers, // ← добавить
];
```

# Graph Service Frontend

## Описание
React SPA для визуализации и редактирования графов дорожных сетей карьера. Приложение предоставляет интерактивный 2D редактор графов и 3D визуализацию с real-time трекингом транспортных средств через WebSocket.

## Основной функционал
- **Интерактивный 2D редактор** графов с Canvas для создания узлов, ребер и меток
- **3D визуализация** с использованием Three.js для пространственного отображения графа
- **Real-time трекинг** транспортных средств через Socket.IO WebSocket
- **Многоуровневая структура** графа с поддержкой вертикальных лестниц между уровнями
- **Настройки GPS топиков** для фильтрации отслеживаемого транспорта
- **Поиск меток** по координатам для определения текущей позиции транспорта
- **Построение маршрутов** между узлами графа

## Технологический стек

### Core Technologies
- **React 18.2.0** - UI библиотека
- **TypeScript 4.9.5** - Type safety
- **Create React App 5.0.1** - Build tooling и development server

### 3D Visualization
- **Three.js 0.159.0** - 3D графический движок
- **@react-three/fiber 8.15.0** - React renderer для Three.js
- **@react-three/drei 9.92.0** - Полезные хелперы для Three.js

### Communication
- **Socket.IO Client 4.7.0** - Real-time WebSocket коммуникация
- **Axios 1.6.0** - HTTP клиент для REST API

### Routing & State
- **React Router DOM 6.8.0** - Client-side routing
- **React Hooks** - Управление состоянием (useState, useEffect, useCallback)

### Development
- **React Scripts 5.0.1** - Build scripts и webpack конфигурация
- **Nginx** - Production static file server + reverse proxy

## Структура приложения

```
graph-service-frontend/
├── public/
│   └── index.html                    # HTML template
├── src/
│   ├── components/                   # React компоненты
│   │   ├── editor/                   # Компоненты редактора
│   │   │   ├── EditorToolbar.tsx     # Панель инструментов редактора
│   │   │   ├── SettingsPage.tsx      # Страница настроек GPS топиков
│   │   │   ├── VehiclesPanel.tsx     # Панель отслеживания транспорта
│   │   │   └── index.ts              # Barrel export
│   │   ├── three/                    # Three.js компоненты
│   │   │   ├── NodeSphere.tsx        # 3D сфера узла
│   │   │   ├── EdgeLine.tsx          # 3D линия ребра
│   │   │   ├── TagSphere.tsx         # 3D сфера метки
│   │   │   ├── VehicleSphere.tsx     # 3D сфера транспорта
│   │   │   ├── SpiralEdge.tsx        # Спиральная лестница
│   │   │   └── index.ts              # Barrel export
│   │   ├── shared/                   # Общие компоненты
│   │   │   ├── AppHeader.tsx         # Header приложения
│   │   │   └── index.ts              # Barrel export
│   │   ├── GraphEditor.tsx           # Главная страница 2D редактора
│   │   ├── GraphEditor.css           # Стили редактора
│   │   ├── ThreeView.tsx             # Страница 3D визуализации
│   │   └── ThreeView.css             # Стили 3D view
│   ├── hooks/                        # Custom React hooks
│   │   ├── useGraphData.ts           # Хук для работы с данными графа
│   │   ├── useWebSocket.ts           # Хук для Socket.IO подключения
│   │   ├── useSettings.ts            # Хук для настроек приложения
│   │   └── index.ts                  # Barrel export
│   ├── services/                     # API сервисы
│   │   └── api.ts                    # REST API клиент (axios)
│   ├── types/                        # TypeScript типы
│   │   └── graph.ts                  # Типы для графов, узлов, ребер
│   ├── App.tsx                       # Корневой компонент с роутингом
│   ├── App.css                       # Глобальные стили
│   ├── index.tsx                     # Точка входа приложения
│   └── index.css                     # Базовые стили
├── package.json                      # Зависимости и скрипты
├── tsconfig.json                     # TypeScript конфигурация
├── Dockerfile                        # Multi-stage build для production
├── nginx.conf                        # Nginx конфигурация
└── README.md                         # Документация проекта
```

## Архитектура приложения

### Страницы и роутинг
```typescript
// src/App.tsx
<Router>
  <Routes>
    <Route path="/" element={<GraphEditor />} />      // 2D редактор графов
    <Route path="/3d-view" element={<ThreeView />} />  // 3D визуализация
  </Routes>
</Router>
```

#### GraphEditor (/)
Главная страница с 2D Canvas редактором:
- Canvas для рисования графа (узлы, ребра, метки)
- Toolbar с инструментами: draw (рисование), move (перемещение), select (выбор), ladder (лестницы)
- Info Panel для отображения информации о выбранных объектах
- Vehicles Panel для отслеживания транспорта в real-time
- Settings Page для настройки GPS топиков MQTT

#### ThreeView (/3d-view)
Страница 3D визуализации:
- Three.js сцена с узлами (сферы), ребрами (линии), метками (цветные сферы)
- Спиральные лестницы между уровнями графа
- Real-time отображение позиции транспорта
- Camera controls с предустановками для разных углов обзора

### Custom Hooks

#### useGraphData
Хук для работы с данными графа через REST API:
```typescript
const {
  levels,           // Список уровней графа
  selectedLevel,    // Выбранный уровень
  graphData,        // Данные графа (nodes, edges, tags)
  isLoading,        // Состояние загрузки
  error,            // Ошибка загрузки
  setSelectedLevel, // Выбор уровня
  loadLevels,       // Загрузка уровней
  loadGraphData,    // Загрузка данных графа
  refreshGraph,     // Обновление графа
} = useGraphData();
```

**Функционал:**
- Автоматическая загрузка уровней при монтировании
- Автоматическая загрузка данных графа при выборе уровня
- Обработка ошибок загрузки
- Состояние загрузки для UI feedback

#### useWebSocket
Хук для Socket.IO подключения и real-time трекинга транспорта:
```typescript
const {
  vehiclePosition,  // Последняя позиция транспорта
  vehicles,         // Все отслеживаемые транспортные средства
  isConnected,      // Статус WebSocket подключения
  clearVehicles,    // Очистка списка транспорта
} = useWebSocket({
  gpsTopics: ['truck/6_truck/sensor/gps/ds'],
  onVehicleUpdate: (position) => {
    console.log('Vehicle updated:', position);
  }
});
```

**Функционал:**
- Socket.IO подключение с автоматическим reconnect
- Фильтрация транспорта по GPS топикам
- Обогащение данных транспорта текущей меткой (через findNearestTag API)
- Обработка событий: `vehicle_location_update`, `connected`, `disconnect`

#### useSettings
Хук для управления настройками приложения:
```typescript
const {
  gpsTopics,              // Список GPS топиков для фильтрации
  defaultVehicleZ,        // Высота транспорта по умолчанию
  transformGPStoCanvas,   // Преобразование GPS → Canvas координаты
  // ... другие настройки
} = useSettings();
```

### API Services

#### REST API Client (src/services/api.ts)
Axios клиент для работы с backend API:

**Уровни:**
```typescript
getLevels(): Promise<Level[]>                      // Получить все уровни
createLevel(levelData): Promise<Level>             // Создать уровень
getLevel(levelId): Promise<Level>                  // Получить уровень по ID
deleteLevel(levelId): Promise<any>                 // Удалить уровень
```

**Граф:**
```typescript
getLevelGraph(levelId): Promise<GraphData>         // Получить данные графа
createNode(levelId, nodeData): Promise<any>        // Создать узел
createEdge(levelId, edgeData): Promise<any>        // Создать ребро
```

**Метки:**
```typescript
createTag(tagData): Promise<Tag>                   // Создать метку
findNearestTag(location): Promise<LocationResponse> // Найти ближайшую метку
```

**Лестницы:**
```typescript
createLadder(levelId, ladderData): Promise<any>    // Создать лестницу
getLadderNodes(levelId): Promise<any[]>            // Получить лестницы
deleteLadder(nodeId): Promise<any>                 // Удалить лестницу
```

**Маршруты:**
```typescript
findRoute(routeData): Promise<RouteResponse>       // Найти маршрут между метками
findRouteBetweenNodes(request): Promise<NodeRouteResponse> // Маршрут между узлами
```

**Статистика:**
```typescript
getGraphStats(levelId): Promise<GraphStats>        // Статистика графа
rebuildGraph(levelId): Promise<any>                // Перестроение графа
```

### TypeScript типы

#### Основные типы (src/types/graph.ts)
```typescript
interface Level {
  id: number;
  name: string;
  height: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

interface GraphNode {
  id: number;
  level_id: number;
  x: number;
  y: number;
  z: number;
  node_type: string;
}

interface GraphEdge {
  id: number;
  level_id: number | null;
  from_node_id: number;
  to_node_id: number;
  edge_type?: string;
}

interface Tag {
  id: number;
  level_id: number;
  x: number;
  y: number;
  z: number;
  radius: number;
  name: string;
  point_type: string;
  point_id: string;
}

interface VehiclePosition {
  vehicle_id: string;
  lat: number;
  lon: number;
  height?: number;
  timestamp: number;
  currentTag?: LocationResponse | null;
}
```

## API Integration

### REST API через Nginx Proxy
Все запросы к `/api` автоматически проксируются на `backend:5000` через Nginx:

```typescript
// src/services/api.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Пример использования
const levels = await getLevels();
const graphData = await getLevelGraph(levelId);
```

### WebSocket через Socket.IO
Socket.IO подключение автоматически проксируется через `/socket.io`:

```typescript
// src/hooks/useWebSocket.ts
import { io, Socket } from 'socket.io-client';

const socket: Socket = io(window.location.origin, {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionAttempts: 5
});

// Подписка на события
socket.on('connect', () => {
  console.log('Socket.IO connected');
  socket.emit('join_vehicle_tracking');
});

socket.on('vehicle_location_update', async (data: VehiclePosition) => {
  // Фильтрация по GPS топикам
  const allowedVehicleIds = gpsTopics.map(topic => {
    const match = topic.match(/truck\/([^\/]+)\//);
    return match ? match[1] : null;
  }).filter(Boolean);
  
  if (allowedVehicleIds.includes(data.vehicle_id)) {
    // Обогащение данных текущей меткой
    const currentTag = await findNearestTag(data.lat, data.lon);
    const enrichedData = { ...data, currentTag };
    
    setVehiclePosition(enrichedData);
  }
});
```

## Установка и запуск

### Локальная разработка
```bash
# Установка зависимостей
npm install

# Запуск dev server с hot reload
npm start

# Приложение доступно на http://localhost:3000
```

### Production Build
```bash
# Сборка production build
npm run build

# Файлы будут в директории ./build

# Preview сборки локально
npx serve -s build
```

### Docker Deployment
```bash
# Сборка Docker образа
docker build -t graph-service-frontend .

# Запуск контейнера
docker run -p 3000:80 graph-service-frontend

# Frontend доступен на http://localhost:3000
# API прокси: /api → backend:5000
# WebSocket прокси: /socket.io → backend:5000
```

## Конфигурация

### Environment Variables

#### API Configuration
Для production не требуются - Nginx проксирует все запросы к backend.

Для development (опционально):
```bash
# .env
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_WS_URL=http://localhost:5000
```

#### Enterprise Service Configuration
```bash
# Адрес Enterprise Service для получения списка транспорта
# Бортовой режим: обращаемся к локальному enterprise-service
REACT_APP_ENTERPRISE_SERVICE_HOST=enterprise-service
REACT_APP_ENTERPRISE_SERVICE_PORT=8001
```

#### Application Mode Configuration

Приложение поддерживает два режима работы:

**1. Серверный режим (Server Mode)** - по умолчанию:
```bash
REACT_APP_MODE=server
```
- Загружает все машины из Enterprise Service при старте
- Создает 3D модели/точки для всех машин на "гараже"
- Машины обновляются через WebSocket
- **Используется:** для диспетчерских центров, мониторинга всего автопарка

**2. Бортовой режим (Onboard Mode)** - для установки на технику:
```bash
REACT_APP_MODE=onboard
```
- НЕ загружает все машины при старте
- Показывает только те машины, от которых приходят WebSocket данные
- Экономит ресурсы и трафик
- **Используется:** для бортовых компьютеров на технике

#### Garage (Initial Position) Configuration

⚠️ **Важно:** Используется только в **серверном режиме** (REACT_APP_MODE=server)

Начальная позиция "гаража" где появляется вся техника до получения real-time данных:

```bash
# GPS координаты гаража (градусы)
REACT_APP_GARAGE_LAT=0
REACT_APP_GARAGE_LON=0

# Высота гаража (метры)
REACT_APP_GARAGE_HEIGHT=0
```

**Пример конфигурации для серверного режима:**
```bash
# Серверный режим для диспетчерской
REACT_APP_MODE=server
REACT_APP_GARAGE_LAT=58.170120
REACT_APP_GARAGE_LON=59.829150
REACT_APP_GARAGE_HEIGHT=-800
```

**Пример конфигурации для бортового режима:**
```bash
# Бортовой режим - координаты гаража не нужны
REACT_APP_MODE=onboard
```

**Как работает серверный режим:**
1. При загрузке создаются модели для всей техники из Enterprise Service
2. Вся техника изначально размещается на координатах гаража
3. Когда приходят real-time данные через WebSocket, техника перемещается на актуальные позиции
4. Если для техники нет real-time данных, она остается на гараже

**Как работает бортовой режим:**
1. При загрузке НЕ создаются начальные модели
2. Машины появляются только когда приходят WebSocket данные
3. Отображаются только активные машины с real-time данными
4. Меньше нагрузка на систему и сеть

### Nginx Configuration
Конфигурация в `nginx.conf`:

#### Frontend Serving
```nginx
# React SPA с fallback на index.html для client-side routing
location / {
    try_files $uri $uri/ /index.html;
}
```

#### API Proxy
```nginx
# Проксирование REST API запросов к backend
location /api {
    proxy_pass http://backend;  # upstream backend = graph-service-backend:5000
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CORS headers
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
}
```

#### WebSocket Proxy
```nginx
# Проксирование Socket.IO WebSocket подключений
location /socket.io {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    
    # WebSocket timeouts
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

#### Health Check
```nginx
# Health check endpoint для container health checks
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}
```

#### Caching Strategy
```nginx
# Агрессивный кеш для статических файлов (JS, CSS, images)
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# No-cache для index.html (чтобы всегда загружать свежую версию)
location = /index.html {
    expires -1;
    add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate";
}
```

## Development Guidelines

### Добавление нового компонента
```bash
# Создать компонент в src/components/
mkdir -p src/components/MyComponent
touch src/components/MyComponent/MyComponent.tsx
touch src/components/MyComponent/MyComponent.css
touch src/components/MyComponent/index.ts

# Экспорт компонента
echo "export { default } from './MyComponent';" > src/components/MyComponent/index.ts
```

```typescript
// src/components/MyComponent/MyComponent.tsx
import React from 'react';
import './MyComponent.css';

interface MyComponentProps {
  title: string;
  onAction?: () => void;
}

function MyComponent({ title, onAction }: MyComponentProps) {
  return (
    <div className="my-component">
      <h2>{title}</h2>
      <button onClick={onAction}>Action</button>
    </div>
  );
}

export default MyComponent;
```

### Добавление нового API endpoint
```typescript
// src/services/api.ts
export const getMyData = async (): Promise<MyData> => {
  const response = await api.get('/my-endpoint');
  return response.data;
};

export const createMyData = async (data: MyDataCreate): Promise<MyData> => {
  const response = await api.post('/my-endpoint', data);
  return response.data;
};
```

### Добавление нового WebSocket события
```typescript
// В компоненте или хуке
useEffect(() => {
  const socket = io(window.location.origin);
  
  socket.on('my_custom_event', (data) => {
    console.log('Received event:', data);
    // Обработка события
  });
  
  return () => {
    socket.off('my_custom_event');
    socket.disconnect();
  };
}, []);
```

### Создание нового custom hook
```typescript
// src/hooks/useMyCustomHook.ts
import { useState, useEffect, useCallback } from 'react';

export function useMyCustomHook(param: string) {
  const [data, setData] = useState<MyData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await fetchMyData(param);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [param]);
  
  useEffect(() => {
    loadData();
  }, [loadData]);
  
  return { data, isLoading, error, reload: loadData };
}
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Nginx (port 3000) - Reverse Proxy              │
├─────────────────────────────────────────────────────────────┤
│  Location /          → React SPA (static files in /build)   │
│  Location /api       → Proxy to backend:5000                │
│  Location /socket.io → Proxy to backend:5000 (WebSocket)    │
│  Location /health    → Health check (200 OK)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│       Graph Service Backend (Flask + Socket.IO)             │
│                    Port: 5000                                │
├─────────────────────────────────────────────────────────────┤
│  REST API:                                                   │
│    - /api/levels          - Управление уровнями             │
│    - /api/graph           - Данные графа                    │
│    - /api/location/find   - Поиск меток                     │
│    - /api/route/find      - Построение маршрутов            │
│                                                              │
│  WebSocket:                                                  │
│    - vehicle_location_update  - Real-time позиции           │
│    - join_vehicle_tracking    - Подписка на трекинг         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │   Database   │
                  └──────────────┘
```

### Docker Multi-stage Build
```dockerfile
# Stage 1: Build React application
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
```

## Troubleshooting

### Проблемы с WebSocket подключением
```bash
# Проверить логи Nginx
docker logs graph-service-frontend

# Проверить логи backend
docker logs graph-service-backend

# Проверить WebSocket через браузер
# В DevTools → Network → WS должно быть подключение к /socket.io
```

### Проблемы с API запросами
```bash
# Проверить доступность API
curl http://localhost:3000/api/levels

# Проверить CORS headers
curl -I http://localhost:3000/api/levels

# Проверить backend напрямую
curl http://localhost:5000/api/levels
```

### Проблемы с Docker build
```bash
# Очистить Docker cache
docker builder prune

# Пересобрать с нуля
docker build --no-cache -t graph-service-frontend .

# Проверить логи контейнера
docker logs -f graph-service-frontend
```


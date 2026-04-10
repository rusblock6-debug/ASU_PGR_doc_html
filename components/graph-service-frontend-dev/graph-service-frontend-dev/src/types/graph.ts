/**
 * TypeScript типы для graph-service frontend
 */

export interface Horizon {
  id: number;
  name: string;
  height: number;
  color?: string;  // HEX цвет для визуализации (#RRGGBB)
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Place {
  id: number;
  name: string;
  type: string;  // load, unload, reload, transit, park
  location?: {
    x: number;
    y: number;
    lat?: number;
    lon?: number;
  } | GeoJSONPoint | null;
  horizon_id?: number | null;
  horizon?: Horizon | null;
  cargo_type?: number | null;
  created_at: string;
  updated_at: string;
}

// Minimal GeoJSON Point support for backend responses
export interface GeoJSONPoint {
  type: 'Point';
  coordinates: [number, number] | number[];
}

export interface GraphNode {
  id: number;
  horizon_id: number;
  x: number;
  y: number;
  z: number;
  node_type: string;
  created_at: string;
  updated_at: string;
}

export interface GraphEdge {
  id: number;
  horizon_id: number | null;
  from_node_id: number;
  to_node_id: number;
  edge_type?: string;
  weight?: number;  // Вес ребра (опционально, для взвешенных графов)
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  place_id?: number | null;  // ID места, к которому привязана метка
  place?: Place | null;  // Объект места (с horizon_id, location)
  radius: number;  // beacon_radius - радиус действия
  tag_id: string;  // Уникальная ID метки
  tag_mac: string;  // MAC адрес метки
  battery_level?: number | null;  // beacon_power - уровень заряда (0-100, только для чтения)
  battery_updated_at?: string | null;  // Дата изменения уровня заряда
  created_at: string;
  updated_at: string;

  // Вычисляемые поля (для обратной совместимости)
  x?: number;  // Координата X из place.location
  y?: number;  // Координата Y из place.location
  z?: number;  // Высота из place.horizon.height
  horizon_id?: number;  // ID горизонта из place.horizon_id
  name?: string;  // Название места
  point_type?: string;  // Тип места
  point_id?: string;  // tag_id для обратной совместимости
  beacon_id?: string;  // tag_id для обратной совместимости
  beacon_mac?: string;  // tag_mac для обратной совместимости
  beacon_place?: string;  // Название места
}

export interface GraphData {
  horizon?: Horizon;
  nodes: GraphNode[];
  edges: GraphEdge[];
  tags: Tag[];
  places?: Place[]; // new source of coordinates for map markers
}

export interface VehicleLocation {
  vehicle_id: string;
  lat: number;
  lon: number;
  height?: number;
  timestamp: string;
}

export interface LocationRequest {
  lat: number;
  lon: number;
  height?: number;
}

export interface LocationResponse {
  point_id: string | null;
  point_name: string | null;
  point_type: string | null;
}

// Canvas rendering types
export interface CanvasNode {
  id: number;
  x: number;
  y: number;
  z: number;
  type: string;
  label?: string;
}

export interface CanvasEdge {
  from: number;
  to: number;
  weight?: number;
}

export interface CanvasTag {
  id: number;
  x: number;
  y: number;
  z: number;
  radius: number;
  name: string;
  tag_id: string;
  place_type: string;
  place_name: string;
}

export interface VehiclePosition {
  vehicle_id: string;
  name?: string;  // Название машины из enterprise-service
  lat: number;  // Оригинальные GPS координаты (широта)
  lon: number;  // Оригинальные GPS координаты (долгота)
  height?: number;
  speed?: number;  // Скорость (км/ч)
  weight?: number;  // Вес груза (тонны)
  fuel?: number;  // Уровень топлива (л или %)
  state?: string;  // State Machine статус (idle, moving_empty, loading, etc.)
  tag?: {  // Текущая метка из eKuiper события
    point_id: string;
    point_name: string;
    point_type: string;
  } | null;
  task_id?: string | null;  // ID задания для получения маршрута
  trip_type?: 'planned' | 'unplanned' | null;  // Тип рейса
  timestamp: number;
  currentTag?: LocationResponse | null; // Текущая метка в которой находится грузовик (legacy)
  canvasX?: number;  // Canvas координаты для 3D (опционально)
  canvasY?: number;  // Canvas координаты для 3D (опционально)
  prevCanvasX?: number;  // Предыдущая позиция для вычисления направления
  prevCanvasY?: number;  // Предыдущая позиция для вычисления направления
  rotation?: number;  // Угол поворота в радианах (вычисляется автоматически)
}
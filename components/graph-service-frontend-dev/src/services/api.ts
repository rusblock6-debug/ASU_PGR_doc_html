/**
 * API сервис для graph-service frontend
 */
import axios from 'axios';
import {
  Horizon,
  GraphData,
  Tag,
  Place
} from '../types/graph';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  transformResponse: [(data) => {
    if (!data) return data;
    try {
      return JSON.parse(data);
    } catch (e) {
      console.error('JSON parse error:', e, 'Data:', data);
      return data;
    }
  }],
});

// Интерфейс пагинированного ответа
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  pages: number;
  size: number;
  items: T[];
}

// Горизонты
export const getHorizons = async (): Promise<Horizon[]> => {
  try {
    const response = await api.get<PaginatedResponse<Horizon>>('/levels', {
      params: { size: 100 }  // Получаем все горизонты (обычно их немного)
    });
    
    // Гарантируем, что всегда возвращаем массив
    if (response.data) {
      // Проверяем пагинированный ответ
      if (typeof response.data === 'object' && response.data !== null && 'items' in response.data) {
        const items = (response.data as any).items;
        if (Array.isArray(items)) return items;
      }
      if (Array.isArray(response.data)) return response.data;
    }
    return [];
  } catch (error) {
    console.error('getHorizons: API error', error);
    return [];
  }
};

// Горизонты с полной информацией о пагинации
export const getHorizonsPaginated = async (page: number = 1, size: number = 100): Promise<PaginatedResponse<Horizon>> => {
  const response = await api.get<PaginatedResponse<Horizon>>('/levels', {
    params: { page, size }
  });
  return response.data;
};

export const createHorizon = async (horizonData: Partial<Horizon>): Promise<Horizon> => {
  const response = await api.post('/levels', horizonData);
  return response.data;
};

export const getHorizon = async (horizonId: number): Promise<Horizon> => {
  const response = await api.get(`/levels/${horizonId}`);
  return response.data;
};

export const getHorizonObjectsCount = async (horizonId: number): Promise<any> => {
  const response = await api.get(`/levels/${horizonId}/graph/count`);
  return response.data;
};

export const deleteHorizon = async (horizonId: number): Promise<any> => {
  const response = await api.delete(`/levels/${horizonId}`);
  return response.data;
};

// Граф
export const getHorizonGraph = async (horizonId: number): Promise<GraphData> => {
  const response = await api.get(`/levels/${horizonId}/graph`);
  return response.data;
};

export const createNode = async (horizonId: number, nodeData: any): Promise<any> => {
  const response = await api.post('/nodes', { ...nodeData, horizon_id: horizonId });
  return response.data;
};

export const createEdge = async (horizonId: number, edgeData: any): Promise<any> => {
  const response = await api.post('/edges', { ...edgeData, horizon_id: horizonId });
  return response.data;
};

// Места (Places)
export const createPlace = async (placeData: Partial<Place>): Promise<Place> => {
  const response = await api.post('/places', placeData);
  return response.data;
};

// Метки
export const createTag = async (tagData: Partial<Tag>): Promise<Tag> => {
  const response = await api.post('/tags', tagData);
  return response.data;
};

// Лестницы (Ladder nodes)
export const createLadder = async (horizonId: number, ladderData: any): Promise<any> => {
  const response = await api.post(`/levels/${horizonId}/ladder-nodes`, ladderData);
  return response.data;
};

export const connectLadderNodes = async (fromNodeId: number, toNodeId: number): Promise<any> => {
  const response = await api.post(`/ladder-nodes/connect`, {
    from_node_id: fromNodeId,
    to_node_id: toNodeId
  });
  return response.data;
};

export const getLadderNodes = async (horizonId: number): Promise<any[]> => {
  const response = await api.get(`/levels/${horizonId}/ladder-nodes`);
  return response.data;
};

export const deleteLadder = async (nodeId: number): Promise<any> => {
  const response = await api.delete(`/ladder-nodes/${nodeId}`);
  return response.data;
};

// Health check
export const healthCheck = async (): Promise<any> => {
  const response = await api.get('/health');
  return response.data;
};

// Импорт графов
export const importGraph = async (importData: any): Promise<any> => {
  const response = await api.post('/import/graph', importData);
  return response.data;
};

// Enterprise Service API для получения информации о задании
export interface RouteTask {
  id: string;
  shift_task_id: string;
  route_order: number;
  point_a_id: number;
  point_b_id: number;
  planned_trips_count?: number;
  actual_trips_count?: number;
  status?: string;
  route_data?: Record<string, any>;
}

export interface ShiftTask {
  id: string;
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  task_name?: string;
  priority: number;
  status: string;
  task_data?: Record<string, any>;
  route_tasks: RouteTask[];
}

// URL enterprise-service: в браузере — хост текущей страницы (иначе браузер не резолвит enterprise-service)
function getEnterpriseServiceBaseUrl(): string {
  const host = process.env.REACT_APP_ENTERPRISE_SERVICE_HOST
    || (typeof window !== 'undefined' ? window.location.hostname : 'enterprise-service');
  const port = process.env.REACT_APP_ENTERPRISE_SERVICE_PORT || '8002';
  return `http://${host}:${port}`;
}

// Получить информацию о задании из enterprise-service
export const getShiftTask = async (taskId: string): Promise<ShiftTask> => {
  const enterpriseServiceUrl = getEnterpriseServiceBaseUrl();
  const response = await axios.get(`${enterpriseServiceUrl}/api/shift-tasks/${taskId}`);
  return response.data;
};

// Типы для машин из enterprise-service
export interface VehicleModel {
  id: number;
  name: string;
  max_speed?: number;
  tank_volume?: number;
  load_capacity_tons?: number;
  volume_m3?: number;
  created_at: string;
  updated_at: string;
}

export interface EnterpriseVehicle {
  id: number;
  enterprise_id: number;
  vehicle_type: string;  // 'shas' или 'pdm'
  name: string;
  model_id?: number | null;
  model?: VehicleModel | null;  // Объект модели машины
  serial_number?: string;
  registration_number?: string;
  status: string;
  is_active: boolean;
  active_from?: string | null;
  active_to?: string | null;
  engine_power_hp?: number;
  tank_volume?: number;
  capacity_tons?: number;  // для PDM
  bucket_volume_m3?: number;  // для PDM
  payload_tons?: number;  // для SHAS
  dump_body_volume_m3?: number;  // для SHAS
  created_at: string;
  updated_at: string;
}

export interface VehicleListResponse {
  total: number;
  page: number;
  size: number;
  items: EnterpriseVehicle[];
}

// Получить список машин из enterprise-service
export const getVehicles = async (enterpriseId: number = 1): Promise<EnterpriseVehicle[]> => {
  const enterpriseServiceUrl = getEnterpriseServiceBaseUrl();
  const response = await axios.get<VehicleListResponse>(`${enterpriseServiceUrl}/api/vehicles`, {
    params: {
      enterprise_id: enterpriseId,
      is_active: true,
      size: 100  // Получаем все активные машины
    }
  });
  return response.data.items;
};

export default api;
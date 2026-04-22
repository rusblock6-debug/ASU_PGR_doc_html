/**
 * API клиент для Trip Service
 */
import axios from 'axios';

// По умолчанию localhost для локальной разработки (переопределяется через VITE_API_URL)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
// const VEHICLE_ID = import.meta.env.VITE_VEHICLE_ID || 'AC9'; // Будет использоваться позже

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Типы данных
export interface Task {
  task_id: string;
  shift_id: string;
  shift_task_id?: string;
  place_a_id: number;
  place_b_id: number;
  order: number;
  status: 'pending' | 'active' | 'in_progress' | 'completed' | 'cancelled' | 'paused';
  planned_trips_count?: number;
  actual_trips_count?: number;
  activated_at?: string | null;
  extra_data?: {
    trips_count?: number;
    trip_count?: number; // Алиас для совместимости
    volume?: number;
    weight?: number;
    message?: string;
    message_to_driver?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface RouteTaskResponse {
  id: string;
  shift_task_id: string;
  route_order: number;
  place_a_id: number;
  place_b_id: number;
  planned_trips_count: number;
  actual_trips_count: number;
  status: string;
  route_data?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface ShiftTaskResponse {
  id: string;
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  task_name: string;
  priority: number;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  sent_to_board_at?: string | null;
  acknowledged_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  task_data?: Record<string, any> | null;
  route_tasks: RouteTaskResponse[];
  created_at: string;
  updated_at: string;
}

export interface CreateShiftTaskPayload {
  id: string;
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  task_name: string;
  priority?: number;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  sent_to_board_at?: string;
  acknowledged_at?: string;
  started_at?: string;
  completed_at?: string;
  task_data?: Record<string, any>;
  route_tasks: Array<{
    id?: string;
    route_order: number;
    place_a_id: number;
    place_b_id: number;
    planned_trips_count?: number;
    actual_trips_count?: number;
    status?: string;
    route_data?: Record<string, any>;
  }>;
}

export interface ActiveTask {
  task_id: string;
  shift_id: string;
  place_a_id: number;
  place_b_id: number;
  order: number;
  status: string;
  activated_at?: string;
  extra_data?: {
    trips_count?: number;
    trip_count?: number;
    volume?: number;
    weight?: number;
    message?: string;
    message_to_driver?: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface ActiveTrip {
  cycle_id: string;  // trip_id = cycle_id в JTI
  vehicle_id: string;
  trip_type: 'planned' | 'unplanned';
  task_id: string | null;
  shift_id: string | null;
  start_time: string;
  end_time?: string | null;  // Время завершения рейса (если завершён)
  loading_point_id: string | null;
  loading_tag: string | null;
  current_state: string; // Состояние State Machine
  last_tag: string | null;
  last_point_id: string | null;
}

export interface StateMachineState {
  state: string;
  cycle_id: string | null;
  task_id: string | null;
  last_tag: string | null;
  last_point_id: string | null;
  last_transition: string;
  previous_state?: string | null;
}

export interface VehicleInfo {
  vehicle_id: number;
  name: string | null;
  vehicle_type: string | null;
  model_id: number | null;
  model_name: string | null;
  load_capacity_tons: number | null;
  volume_m3: number | null;
  max_speed: number | null;
  tank_volume: number | null;
  service_mode: string;
}

export interface EventLogHistoryParams {
  from_date: string;
  to_date: string;
  from_shift_num: number;
  to_shift_num: number;
  page?: number;
  size?: number;
}

// API методы
export const tripServiceApi = {
  // Получить все задания
  getTasks: async (params?: { shift_id?: string; status?: string; page?: number; size?: number }) => {
    const response = await apiClient.get<{ items: Task[]; total: number }>('/api/tasks', { params });
    return response.data;
  },

  // Создать задание
  createTask: async (data: {
    task_id: string;
    shift_id: string;
    place_a_id: number;
    place_b_id: number;
    order: number;
    status?: string;
    extra_data?: any;
  }) => {
    const response = await apiClient.post<Task>('/api/tasks', data);
    return response.data;
  },

  // Получить смены
  getShiftTasks: async (params?: { status?: string; page?: number; size?: number }) => {
    const response = await apiClient.get<{ items: ShiftTaskResponse[]; total: number }>('/api/shift-tasks', { params });
    return response.data;
  },

  // Создать смену со заданиями (для импорта JSON)
  createShiftTask: async (data: CreateShiftTaskPayload) => {
    const response = await apiClient.post<ShiftTaskResponse>('/api/shift-tasks', data);
    return response.data;
  },

  // Получить активное задание
  getActiveTask: async (): Promise<Task | null> => {
    try {
      const response = await apiClient.get<Task>('/api/active/task');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // Нет активного задания
      }
      throw error;
    }
  },

  // Получить активный рейс
  getActiveTrip: async (): Promise<ActiveTrip | null> => {
    try {
      const response = await apiClient.get<ActiveTrip>('/api/active/trip');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // Нет активного рейса
      }
      throw error;
    }
  },

  // Получить количество завершенных рейсов для задания
  getCompletedTripsCount: async (taskId: string) => {
    // Передаем параметры напрямую в URL, чтобы убедиться что они передаются
    const response = await apiClient.get<{ items: any[]; total: number }>(
      `/api/trips?task_id=${taskId}&completed_only=true`
    );
    return response.data.total || 0;
  },

  // Получить текущее состояние State Machine
  getCurrentState: async (): Promise<StateMachineState> => {
    const response = await apiClient.get<StateMachineState>('/api/state');
    return response.data;
  },

  // Обновить задание
  updateTask: async (taskId: string, data: Partial<Task>) => {
    const response = await apiClient.put<Task>(`/api/tasks/${taskId}`, data);
    return response.data;
  },

  // Деактивировать текущее задание
  deactivateTask: async () => {
    const response = await apiClient.delete('/api/active/task');
    return response.data;
  },

  // Активировать задание (автоматически приостанавливает предыдущее)
  activateTask: async (taskId: string) => {
    const response = await apiClient.put<Task>(`/api/tasks/${taskId}/activate`);
    return response.data;
  },

  // Приостановить задание
  pauseTask: async (taskId: string) => {
    const response = await apiClient.put<Task>(`/api/tasks/${taskId}`, {
      status: 'paused',
    });
    return response.data;
  },

  // Получить историю состояний
  getStateHistory: async (params: EventLogHistoryParams) => {
    const response = await apiClient.get<{ items: any[]; total: number; page: number; size: number; pages: number }>(
      '/api/event-log/state-history',
      { params }
    );
    return response.data;
  },

  // Получить историю меток
  getTagHistory: async (params: EventLogHistoryParams) => {
    const response = await apiClient.get<{ items: any[]; total: number; page: number; size: number; pages: number }>(
      '/api/event-log/tag-history',
      { params }
    );
    return response.data;
  },

  // Выполнить переход состояния вручную
  transitionState: async (data: { new_state: string; reason?: string; comment?: string }) => {
    const response = await apiClient.post('/api/state/transition', data);
    return response.data;
  },

  // Получить статистику рейсов
  getTripAnalytics: async (params?: { page?: number; size?: number; vehicle_id?: string; from_date?: string; to_date?: string }) => {
    // Используем правильный endpoint /api/trips/analytics для получения аналитики
    const response = await apiClient.get<{ items: any[]; total: number; page: number; size: number; pages: number }>(
      '/api/trips/analytics',
      { params }
    );
    
    // Данные уже в правильном формате из CycleAnalyticsResponse
    // Просто маппим cycle_id в internal_trip_id для совместимости с фронтендом
    const transformedItems = response.data.items.map((analytics: any) => ({
      id: analytics.id,
      internal_trip_id: analytics.cycle_id, // cycle_id = trip_id в JTI
      vehicle_id: analytics.vehicle_id,
      shift_id: analytics.shift_id,
      trip_type: analytics.trip_type,
      trip_status: analytics.trip_status,
      from_point_id: analytics.from_point_id,
      to_point_id: analytics.to_point_id,
      trip_started_at: analytics.trip_started_at,
      trip_completed_at: analytics.trip_completed_at,
      total_duration_seconds: analytics.total_duration_seconds,
      moving_empty_duration_seconds: analytics.moving_empty_duration_seconds,
      stopped_empty_duration_seconds: analytics.stopped_empty_duration_seconds,
      loading_duration_seconds: analytics.loading_duration_seconds,
      moving_loaded_duration_seconds: analytics.moving_loaded_duration_seconds,
      stopped_loaded_duration_seconds: analytics.stopped_loaded_duration_seconds,
      unloading_duration_seconds: analytics.unloading_duration_seconds,
      state_transitions_count: analytics.state_transitions_count,
      analytics_data: analytics.analytics_data,
      created_at: analytics.created_at,
      updated_at: analytics.updated_at,
    }));

    return {
      ...response.data,
      items: transformedItems,
    };
  },

  // Получить информацию о транспорте
  getVehicleInfo: async (): Promise<VehicleInfo> => {
    const response = await apiClient.get<VehicleInfo>('/api/state/vehicle-info');
    return response.data;
  },
};


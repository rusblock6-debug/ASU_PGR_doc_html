import axios from 'axios';
import type {
  ShiftTask,
  ShiftTaskCreate,
  ShiftTaskListResponse,
  ShiftTaskBulkUpsertRequest,
  StatusListResponse,
  DispatcherAssignmentCreateRequest,
  DispatcherAssignmentResponse,
  UnusedVehiclesResponse,
  Vehicle,
  VehicleListResponse,
  WorkRegime,
  WorkRegimeListResponse,
  Place,
  PlaceListResponse,
  EventLogListResponse,
  CycleStateHistoryItem,
  RouteSummaryResponse,
  ReassignVehicleRequest,
  ReassignVehicleResponse,
  RouteTemplateCreateRequest,
  RouteTemplateResponse,
  RouteTemplateUpdateRequest,
} from '../types';

const API_BASE_URL = '/api';
const GRAPH_API_BASE_URL = '/graph-api';
/** Trip-service (dispa-backend): сменные задания, маршруты, event-log и т.д. */
const TRIP_API_BASE_URL = '/trip-api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/** Клиент для trip-service — сменные задания переехали из enterprise-service сюда. */
export const tripApi = axios.create({
  baseURL: TRIP_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const graphApi = axios.create({
  baseURL: GRAPH_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Shift Tasks API (trip-service)
export const shiftTasksApi = {
  list: async (params?: {
    enterprise_id?: number;
    shift_date?: string;
    vehicle_id?: number;
    vehicle_ids?: number[];
    shift_num?: number;
    page?: number;
    size?: number;
  }): Promise<ShiftTaskListResponse> => {
    // Устанавливаем значения по умолчанию
    const requestParams: Record<string, unknown> = {
      enterprise_id: 1,
      page: 1,
      size: 20,
      ...params,
    };
    if (params?.vehicle_ids?.length) {
      requestParams.vehicle_ids = params.vehicle_ids;
    }
    const response = await tripApi.get('/shift-tasks', { params: requestParams });
    return response.data;
  },

  bulkUpsert: async (data: ShiftTaskBulkUpsertRequest): Promise<boolean> => {
    const response = await tripApi.post('/shift-tasks/bulk-upsert', data);
    return response.data === true;
  },

  create: async (data: ShiftTaskCreate): Promise<ShiftTask> => {
    const response = await tripApi.post('/shift-tasks', data);
    return response.data;
  },

  get: async (taskId: string): Promise<ShiftTask> => {
    const response = await tripApi.get(`/shift-tasks/${taskId}`);
    return response.data;
  },

  update: async (taskId: string, data: Partial<ShiftTaskCreate>): Promise<ShiftTask> => {
    const response = await tripApi.put(`/shift-tasks/${taskId}`, data);
    return response.data;
  },

  delete: async (taskId: string): Promise<void> => {
    await tripApi.delete(`/shift-tasks/${taskId}`);
  },

  save: async (data: ShiftTaskCreate): Promise<ShiftTask> => {
    const response = await tripApi.post('/shift-tasks/save', data);
    return response.data;
  },

  approve: async (taskId: string, data: Partial<ShiftTaskCreate>): Promise<ShiftTask> => {
    const response = await tripApi.post(`/shift-tasks/${taskId}/approve`, data);
    return response.data;
  },
};

// Statuses API (enterprise-service, для цвета и is_work_status)
export const statusesApi = {
  list: async (params?: { page?: number; size?: number }): Promise<StatusListResponse> => {
    const response = await api.get('/statuses', { params });
    return response.data;
  },
};

// Vehicles API
export const vehiclesApi = {
  list: async (params?: { 
    enterprise_id?: number;
    is_active?: boolean;
    vehicle_type?: string;
    page?: number;
    size?: number;
  }): Promise<VehicleListResponse> => {
    const response = await api.get('/vehicles', { params });
    return response.data;
  },

  get: async (vehicleId: number): Promise<Vehicle> => {
    const response = await api.get(`/vehicles/${vehicleId}`);
    return response.data;
  },
};

// Work Regimes API
export const workRegimesApi = {
  list: async (params?: {
    enterprise_id?: number;
    is_active?: boolean;
    page?: number;
    size?: number;
  }): Promise<WorkRegimeListResponse> => {
    const response = await api.get('/work-regimes', { params });
    return response.data;
  },

  get: async (regimeId: number): Promise<WorkRegime> => {
    const response = await api.get(`/work-regimes/${regimeId}`);
    return response.data;
  },

  // Получить активный режим работы (по умолчанию ID=1)
  getActive: async (): Promise<WorkRegime> => {
    return workRegimesApi.get(1);
  },
};

// Places API (Graph Service)
export const placesApi = {
  list: async (params?: {
    type?: 'load' | 'unload';
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<PlaceListResponse> => {
    const response = await graphApi.get('/places', { params });
    return response.data;
  },

  get: async (placeId: number): Promise<Place> => {
    const response = await graphApi.get(`/places/${placeId}`);
    return response.data;
  },
};

type StateHistoryQueryParams = {
  from_date: string;
  to_date: string;
  from_shift_num?: number;
  to_shift_num?: number;
  vehicle_ids?: number[];
  page?: number;
  size?: number;
};

export const eventLogApi = {
  getStateHistory: async (
    params: StateHistoryQueryParams,
  ): Promise<EventLogListResponse<CycleStateHistoryItem>> => {
    const response = await axios.get('/api/event-log/state-history', { params });
    return response.data;
  },
};

// Cycle History API
export type CycleStateHistoryBatchItem = {
  id?: string;
  timestamp: string;
  system_name: string;
  system_status?: boolean;
};

export type CycleStateHistoryBatchRequest = {
  items: CycleStateHistoryBatchItem[];
};

export type CycleStateHistoryBatchResultItem = {
  id: string;
  operation: string;
  state: string;
  timestamp: string;
  cycle_id?: string;
  cycle_action?: string;
};

export type CycleStateHistoryBatchResponse = {
  success: boolean;
  message: string;
  results: CycleStateHistoryBatchResultItem[];
  cycles_created: number;
  cycles_completed: number;
};

export type StateHistoryDeleteRequest = {
  confirm: boolean;
};

export type StateHistoryDeleteResponse = {
  success: boolean;
  message: string;
  cycle_id?: string;
  deleted_record_id?: string;
  cycle_deleted: boolean;
  trip_deleted: boolean;
  fields_cleared: string[];
};

// Route Summary API (trip-service)
export const routeSummaryApi = {
  get: async (): Promise<RouteSummaryResponse> => {
    const response = await axios.get('/api/route-summary');
    return response.data;
  },

  getUnusedVehicles: async (): Promise<UnusedVehiclesResponse> => {
    const response = await axios.get('/api/route-summary/unused-vehicles');
    return response.data;
  },

  reassign: async (data: ReassignVehicleRequest): Promise<ReassignVehicleResponse> => {
    const response = await axios.post('/api/route-summary/reassign', data);
    return response.data;
  },

  createAssignment: async (
    data: DispatcherAssignmentCreateRequest,
  ): Promise<DispatcherAssignmentResponse> => {
    const response = await axios.post('/api/route-summary/assignments', data);
    return response.data;
  },

  decideAssignment: async (
    assignmentId: number,
    approved: boolean,
  ): Promise<DispatcherAssignmentResponse> => {
    const response = await axios.post(`/api/route-summary/assignments/${assignmentId}/decision`, { approved });
    return response.data;
  },

  rejectRouteTask: async (data: {
    vehicle_id: number;
    place_a_id: number;
    place_b_id: number;
  }): Promise<RouteTemplateResponse> => {
    const response = await axios.post('/api/route-summary/reject-route-task', data);
    return response.data;
  },

  createRoute: async (data: RouteTemplateCreateRequest): Promise<RouteTemplateResponse> => {
    const response = await axios.post('/api/route-summary/routes', data);
    return response.data;
  },

  updateRoute: async (data: RouteTemplateUpdateRequest): Promise<RouteTemplateResponse> => {
    const response = await axios.post('/api/route-summary/routes/update-places', data);
    return response.data;
  },
};

export const cycleHistoryApi = {
  batchUpsert: async (
    data: CycleStateHistoryBatchRequest,
  ): Promise<CycleStateHistoryBatchResponse> => {
    console.log('API: batchUpsert', { data });
    const response = await axios.post(`/api/cycle-state-history/batch`, data);
    console.log('API: batchUpsert response', response.data);
    return response.data;
  },

  delete: async (
    recordId: string,
    data: StateHistoryDeleteRequest,
  ): Promise<StateHistoryDeleteResponse> => {
    console.log('API: delete request', { recordId, data });
    try {
      const response = await axios.delete(`/api/cycle-state-history/${recordId}`, {
        data,
      });
      console.log('API: delete response', response.data);
      return response.data;
    } catch (error: any) {
      console.error('API: delete error', error.response?.data || error.message);
      throw error;
    }
  },
};


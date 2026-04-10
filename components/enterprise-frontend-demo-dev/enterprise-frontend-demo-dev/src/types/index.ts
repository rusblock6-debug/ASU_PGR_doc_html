export interface RouteTask {
  id?: string;
  shift_task_id?: string;
  route_order: number;
  planned_trips_count: number;
  actual_trips_count?: number;
  status?: string;
  type_task?: string;
  route_data?: Record<string, any>;
  place_a_id: number; // ID места погрузки (place.id из graph-service)
  place_b_id: number; // ID места разгрузки (place.id из graph-service)
  volume?: number | null;
  weight?: number | null;
  message?: string | null;
  created_at?: string | any; // Backend может вернуть datetime объект
  updated_at?: string | any; // Backend может вернуть datetime объект
}

/** Элемент route_task для bulk-upsert (поля как в API) */
export interface RouteTaskBulkUpsertItem {
  id?: string | null;
  route_order: number;
  shift_task_id: string;
  place_a_id: number;
  place_b_id: number;
  type_task: string;
  planned_trips_count: number;
  actual_trips_count?: number;
  status: string;
  volume?: number | null;
  weight?: number | null;
  message?: string | null;
  route_data?: Record<string, unknown> | null;
}

/** Элемент shift_task для bulk-upsert */
export interface ShiftTaskBulkUpsertItem {
  id?: string | null;
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  shift_num: number;
  priority?: number;
  status?: string;
  route_tasks: RouteTaskBulkUpsertItem[];
}

export interface ShiftTaskBulkUpsertRequest {
  items: ShiftTaskBulkUpsertItem[];
}

export interface ShiftTask {
  id: string;
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  shift_num?: number;
  task_name?: string;
  priority: number;
  status: string;
  task_data?: Record<string, any>;
  sent_to_board_at?: string | null;
  acknowledged_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at?: string;
  updated_at?: string;
  route_tasks?: RouteTask[] | null;
}

export interface ShiftTaskCreate {
  work_regime_id: number;
  vehicle_id: number;
  shift_date: string;
  task_name?: string;
  priority?: number;
  status?: string;
  task_data?: Record<string, any>;
  route_tasks?: RouteTask[];
}

export interface ShiftTaskListResponse {
  total: number;
  page: number;
  size: number;
  items: ShiftTask[];
}

export interface Vehicle {
  id: number;
  enterprise_id: number;
  vehicle_type: string;
  name: string;
  model?: VehicleModel | null;
  serial_number?: string;
  registration_number?: string;
  status: string;
  is_active: boolean;
  // Поля для расчета вместительности
  capacity_volume?: number; // PDM
  bucket_volume_m3?: number; // PDM
  payload_volume?: number; // SHAS - нормативная вместительность
  dump_body_volume_m3?: number; // SHAS
  engine_power_hp?: number;
  tank_volume?: number;
  active_from?: string;
  active_to?: string;
  created_at?: string;
  updated_at?: string;
}

export interface VehicleListResponse {
  total: number;
  page: number;
  size: number;
  items: Vehicle[];
}

export interface ShiftDefinition {
  shift_num: number;
  name?: string;
  begin_offset_minutes?: number;
  end_offset_minutes?: number;
  start_time_offset?: number;
  end_time_offset?: number;
}

export interface WorkRegime {
  id: number;
  enterprise_id: number;
  name: string;
  description?: string;
  is_active: boolean;
  shifts_definition: ShiftDefinition[];
  created_at?: string;
  updated_at?: string;
}

export interface WorkRegimeListResponse {
  total: number;
  page: number;
  size: number;
  items: WorkRegime[];
}

// Типы из граф-сервиса
export interface Place {
  id: number;
  name: string;
  type: 'load' | 'unload' | 'park';
  location?: string;
  available_vehicle_types?: string;
  capacity?: number;
  active_from?: string;
  active_to?: string;
  is_active: boolean;
  primary_remainder?: number;
  current_stock?: number; // Текущий остаток на месте
  tag_point_id?: string; // Ссылка на tag.point_id (строковый идентификатор точки)
}

export interface PlaceListResponse {
  total: number;
  limit: number;
  offset: number;
  items: Place[];
}

export type VehicleState =
  | 'idle'
  | 'moving_empty'
  | 'stopped_empty'
  | 'loading'
  | 'moving_loaded'
  | 'stopped_loaded'
  | 'unloading';

export interface CycleStateHistoryItem {
  id: string;
  timestamp: string;
  vehicle_id: number;
  cycle_id?: string | null;
  state: VehicleState | string;
  source: string;
  task_id?: string | null;
  place_id?: number | null;
}

export interface EventLogListResponse<TItem = CycleStateHistoryItem> {
  items: TItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Модель техники
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

// Route Summary (агрегированные маршруты текущей смены)
export interface RouteSummaryItem {
  place_a_id: number;
  place_b_id: number;
  volume_plan: number;
  volume_fact: number;
  active_vehicles: number[];
  pending_vehicles: number[];
  route_task_ids: string[];
}

export interface RouteSummaryResponse {
  shift_date: string | null;
  shift_num: number | null;
  routes: RouteSummaryItem[];
}

export interface ReassignVehicleRequest {
  vehicle_id: number;
  target_place_a_id: number;
  target_place_b_id: number;
}

export interface ReassignVehicleResponse {
  success: boolean;
  message: string;
  paused_route_task_id: string | null;
  activated_route_task_id: string | null;
}

export interface RouteTemplateCreateRequest {
  place_a_id: number;
  place_b_id: number;
}

export interface RouteTemplateUpdateRequest {
  from_place_a_id: number;
  from_place_b_id: number;
  to_place_a_id: number;
  to_place_b_id: number;
}

export interface RouteTemplateResponse {
  success: boolean;
  message: string;
}

export interface UnusedVehiclesResponse {
  no_task: number[];
  garages: Record<number, number[]>;
  pending_garages: Record<number, number[]>;
  idle: number[];
}

export interface DispatcherAssignmentCreateRequest {
  vehicle_id: number;
  source_kind: 'ROUTE' | 'NO_TASK' | 'GARAGE';
  source_route_place_a_id?: number | null;
  source_route_place_b_id?: number | null;
  source_garage_place_id?: number | null;
  target_kind: 'ROUTE' | 'GARAGE';
  target_route_place_a_id?: number | null;
  target_route_place_b_id?: number | null;
  target_garage_place_id?: number | null;
}

export interface DispatcherAssignmentResponse {
  id: number;
  vehicle_id: number;
  shift_date: string;
  shift_num: number;
  source_kind: string;
  source_route_place_a_id?: number | null;
  source_route_place_b_id?: number | null;
  source_garage_place_id?: number | null;
  target_kind: string;
  target_route_place_a_id?: number | null;
  target_route_place_b_id?: number | null;
  target_garage_place_id?: number | null;
  status: string;
}

/** Статус техники (enterprise-service /api/statuses) для цвета и is_work_status */
export interface Status {
  id: number;
  system_name: string;
  display_name: string;
  color: string;
  is_work_status: boolean;
}

export interface StatusListResponse {
  total: number;
  page: number;
  size: number;
  items: Status[];
}

// Типы заданий
export type TaskType = 'independent' | 'loading_to_shas' | 'household';

export const TASK_TYPES: Record<TaskType, string> = {
  independent: 'Самостоятельные рейсы',
  loading_to_shas: 'Погрузка в ШАС',
  household: 'Хоз. работы',
};


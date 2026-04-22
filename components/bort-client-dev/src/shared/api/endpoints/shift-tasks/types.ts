import type { RouteTaskResponse, TripStatusRouteEnum } from '@/shared/api/endpoints/tasks/types';

/**
 * Сменное задание с набором маршрутных заданий.
 */
export interface ShiftTaskResponse {
  /** Время создания сменного задания. */
  readonly created_at: string;
  /** Время последнего обновления сменного задания. */
  readonly updated_at: string;
  /** ID рабочего режима. */
  readonly work_regime_id: number;
  /** ID транспортного средства/борта. */
  readonly vehicle_id: number;
  /** Дата смены. */
  readonly shift_date: string;
  /** Номер смены. */
  readonly shift_num: number;
  /** Наименование задачи смены. */
  readonly task_name: string | null;
  /** Приоритет задания (как указывает бэкенд). */
  readonly priority: number;
  /** Статус сменного задания. */
  readonly status: string;
  /** Время отправки на борт. */
  readonly sent_to_board_at: string | null;
  /** Время подтверждения (acknowledged). */
  readonly acknowledged_at: string | null;
  /** Время начала выполнения. */
  readonly started_at: string | null;
  /** Время завершения выполнения. */
  readonly completed_at: string | null;
  /** Произвольные данные задания. */
  readonly task_data: Record<string, unknown> | null;
  /** Маршрутные задания, входящие в сменное задание. */
  readonly route_tasks: RouteTaskResponse[];
  /** Идентификатор сменного задания. */
  readonly id: string;
}

/**
 * Полезная нагрузка SSE-события об изменении сменного задания.
 */
export interface ShiftTaskChangedSsePayload {
  /** Тип события (часть SSE-контракта). */
  readonly event_type?: string;
  /** Действие/триггер (часть SSE-контракта). */
  readonly action?: string;
  /** ID сменного задания. */
  readonly shift_task_id?: string;
  /** ID борта/транспортного средства. */
  readonly vehicle_id?: number;
  /** Данные сменного задания (если переданы). */
  readonly shift_task?: ShiftTaskResponse;
  /** Метка времени события. */
  readonly timestamp?: string;
}

/**
 * Параметры запроса списка сменных заданий.
 */
export interface GetShiftTasksArgs {
  readonly page?: number;
  readonly size?: number;
  readonly shift_date?: string;
  readonly vehicle_ids?: number[];
  readonly status_route_tasks?: TripStatusRouteEnum[];
}

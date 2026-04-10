import type { Pagination } from '../../types';

import type { RouteTaskStatus, TypeTaskValue } from './constants';

/**
 * Описание объекта маршрутного задания.
 */
export interface RouteTask {
  /** ID маршрутного задания. */
  readonly id: string;
  /** Тип задания. */
  readonly type_task: TypeTaskValue;
  /** ID смены. */
  readonly shift_task_id: string;
  /** Порядок выполнения. */
  readonly route_order: number;
  /** ID места погрузки. */
  readonly place_a_id: number;
  /** ID места разгрузки. */
  readonly place_b_id: number;
  /** Планируемое количество рейсов. */
  readonly planned_trips_count: number;
  /** Фактическое количество рейсов. */
  readonly actual_trips_count: number;
  /** Статус. */
  readonly status: RouteTaskStatus;
  /** Дополнительные данные JSONB. */
  readonly route_data: Record<string, unknown> | null;
  /** Объем груза. */
  readonly volume: number | null;
  /** Вес груза. */
  readonly weight: number | null;
  /** Сообщение/комментарий. */
  readonly message: string | null;
  /** Время создания записи. ISO 8601 datetime. */
  readonly created_at: string;
  /** Время обновления записи. ISO 8601 datetime. */
  readonly updated_at: string;
}

/** Представляет фильтры дорожных заданий. */
export interface RouteTasksQueryArgs {
  /** Возвращает статус задания. */
  readonly task_status?: RouteTaskStatus | null;
  /** Возвращает идентификатор сменного задания. */
  readonly shift_task_id?: string | null;
  /** Возвращает идентификатор оборудования. */
  readonly vehicle_id?: number | null;
  /** Возвращает идентификатор места погрузки. */
  readonly place_a_id?: number | null;
  /** Возвращает идентификатор места разгрузки. */
  readonly place_b_id?: number | null;
}

/** Представляет модель данных, получаемую по запросу мест. */
export interface RouteTasksResponse extends Pagination {
  /** Возвращает список мест. */
  readonly items: readonly RouteTask[];
}

/**
 * Маршрутное задание внутри наряд-задания.
 *
 * Логика:
 * - `id = undefined/null` → CREATE (генерируется новый ID)
 * - `id указан` → UPDATE (обновляется существующая запись)
 */
export interface RouteTaskUpsertItem {
  /** ID route task (undefined/null = create). */
  readonly id?: string | null;
  /** ID смены. Опционально, заполняется автоматически при вложенности. */
  readonly shift_task_id?: string | null;
  /** Порядок выполнения внутри смены. */
  readonly route_order?: number | null;
  /** ID места погрузки. */
  readonly place_a_id: number;
  /** ID места разгрузки. */
  readonly place_b_id: number;
  /** Тип задания. */
  readonly type_task: TypeTaskValue;
  /** Планируемое количество рейсов. По умолчанию 1. */
  readonly planned_trips_count: number;
  /** Фактическое количество рейсов. По умолчанию 0. */
  readonly actual_trips_count?: number | null;
  /** Статус. По умолчанию 'empty'. */
  readonly status?: RouteTaskStatus;
  /** Дополнительные данные JSONB. */
  readonly route_data?: Record<string, unknown> | null;
  /** Объем груза. */
  readonly volume: number | null;
  /** Вес груза. */
  readonly weight: number | null;
  /** Сообщение/комментарий (до 500 символов). */
  readonly message?: string | null;
}

/**
 * Запрос для bulk upsert route_tasks.
 *
 * Логика:
 * - `id = null/undefined` → CREATE (генерируется новый ID)
 * - `id указан` → UPDATE (обновляется существующая запись)
 */
export interface RouteTaskBulkUpsertRequest {
  /** Список маршрутных заданий */
  readonly items: readonly RouteTaskUpsertItem[];
}

/**
 * Представляет ответ API со списком маршрутных заданий.
 */
export interface RouteTaskBulkUpsertResponse {
  /** Содержит как созданные, так и обновленные записи маршрутных заданий. */
  readonly items: readonly RouteTask[];
}

/**
 * Параметры запроса для активации маршрутного задания.
 */
export interface ActivateRouteTaskRequest {
  /** ID маршрутного задания для активации. */
  readonly taskId: string;
  /** ID транспортного средства. */
  readonly vehicleId: string;
}

/**
 * Параметры запроса для отмены маршрутного задания.
 */
export interface CancelRouteTaskRequest {
  /** ID маршрутного задания для отмены. */
  readonly taskId: string;
  /** ID транспортного средства. */
  readonly vehicleId: string;
}

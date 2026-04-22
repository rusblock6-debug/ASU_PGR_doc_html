import type { RouteTaskStatus, RouteTaskUpsertItem } from '@/shared/api/endpoints/route-tasks';
import type { RouteTask } from '@/shared/api/endpoints/route-tasks';
import type { Pagination } from '@/shared/api/types';

/**
 * Статус выполнения наряд-задания.
 */
export type ShiftTaskStatus = 'pending' | 'completed' | 'cancelled';

/**
 * Модель наряд-задания.
 */
export interface ShiftTask {
  /** Идентификатор наряд-задания. */
  readonly id: string;
  /** Идентификатор режима работы. */
  readonly work_regime_id: number;
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Дата смены в формате YYYY-MM-DD. */
  readonly shift_date: string;
  /** Номер смены. */
  readonly shift_num: number;
  /** Название задания. */
  readonly task_name: string | null;
  /** Приоритет. */
  readonly priority: number;
  /** Статус. */
  readonly status: ShiftTaskStatus;
  /** Время отправки на борт. ISO 8601 datetime. */
  readonly sent_to_board_at: string | null;
  /** Время подтверждения. ISO 8601 datetime. */
  readonly acknowledged_at: string | null;
  /** Время начала. ISO 8601 datetime. */
  readonly started_at: string | null;
  /** Время завершения. ISO 8601 datetime. */
  readonly completed_at: string | null;
  /** Дополнительные данные. Не используется в дальнейшем уберут. */
  readonly task_data: Record<string, unknown> | null;
  /** Вложенные route tasks. */
  readonly route_tasks: readonly RouteTask[];
  /** Время создания записи. ISO 8601 datetime. */
  readonly created_at: string;
  /** Время обновления записи. ISO 8601 datetime. */
  readonly updated_at: string;
}

/**
 * Аргументы запроса списка наряд-заданий.
 */
export interface ShiftTasksQueryArg {
  /** Фильтр по статусу. */
  readonly status?: ShiftTaskStatus;
  /** Фильтр по дате смены (YYYY-MM-DD). */
  readonly shift_date?: string;
  /** Фильтр по IDs транспортных средств. */
  readonly vehicle_ids?: readonly number[];
  /** Фильтр по номеру смены. */
  readonly shift_num?: number;
  /** Фильтр по статусу маршрутных заданий */
  readonly status_route_tasks?: readonly RouteTaskStatus[];
}

/**
 * Ответ на запрос получения списка наряд-заданий.
 */
export interface ShiftTasksResponse extends Pagination {
  readonly items: readonly ShiftTask[];
}

/**
 * Элемент shift_task для bulk upsert.
 *
 * Логика:
 * - `id указан` → UPDATE shift_task (+ route_tasks UPDATE/CREATE/DELETE)
 *   - если `route_tasks = []` — DELETE все route_tasks которые есть но не указаны
 *   - если `route_tasks = null/undefined` — ничего не меняем
 * - `id НЕ указан` → CREATE shift_task (+ route_tasks только CREATE)
 */
export interface ShiftTaskBulkUpsertItem {
  /** Идентификатор наряд-задания (undefined/null = create). */
  readonly id?: string | null;
  /** Идентификатор режима работы. */
  readonly work_regime_id?: number | null;
  /** Идентификатор транспортного средства. */
  readonly vehicle_id?: number | null;
  /** Дата смены (YYYY-MM-DD). */
  readonly shift_date?: string | null;
  /** Номер смены (>= 1). */
  readonly shift_num?: number | null;
  /** Название задания. */
  readonly task_name?: string | null;
  /** Приоритет. */
  readonly priority?: number | null;
  /** Статус. */
  readonly status?: ShiftTaskStatus | null;
  /** Когда отправлено на борт. ISO 8601 datetime. */
  readonly sent_to_board_at?: string | null;
  /** Когда подтверждено. ISO 8601 datetime. */
  readonly acknowledged_at?: string | null;
  /** Когда начато. ISO 8601 datetime. */
  readonly started_at?: string | null;
  /** Когда завершено. ISO 8601 datetime. */
  readonly completed_at?: string | null;
  /** Дополнительные данные JSONB. */
  readonly task_data?: Record<string, unknown> | null;
  /** Вложенные маршрутные задания. */
  readonly route_tasks?: readonly RouteTaskUpsertItem[] | null;
}

/**
 * Запрос для bulk upsert shift_tasks с вложенными route_tasks.
 *
 * Одна транзакция для всех операций (ROLLBACK при ошибке).
 */
export interface ShiftTaskBulkUpsertRequest {
  /** Элементы для upsert. */
  readonly items: readonly ShiftTaskBulkUpsertItem[];
}

/**
 * Ответ на bulk upsert shift_tasks.
 */
export interface ShiftTaskBulkUpsertResponse {
  /** Обработанные shift_tasks с вложенными route_tasks. */
  readonly items: readonly ShiftTask[];
}

/**
 * Тип действия SSE-события shift_task.
 */
export type ShiftTaskStreamAction = 'create' | 'update' | 'delete';

/**
 * SSE-событие изменения shift_task.
 */
export interface ShiftTaskStreamMessage {
  /** Действие: создание, обновление или удаление. */
  readonly action: ShiftTaskStreamAction;
  /** Тип события. */
  readonly event_type: 'shift_task_changed';
  /** Данные shift_task (отсутствует при delete). */
  readonly shift_task?: ShiftTask;
  /** Идентификатор shift_task. */
  readonly shift_task_id: string;
  /** Время события. ISO 8601 datetime. */
  readonly timestamp: string;
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
}

/**
 * Параметры запроса preview-заданий из предыдущей смены.
 */
export interface PreviewFromPreviousShiftRequest {
  /** Идентификатор режима работы. */
  readonly work_regime_id: number;
  /** Дата, на которую адаптировать (YYYY-MM-DD). */
  readonly target_date: string;
  /** Номер смены, на которую адаптировать. */
  readonly target_shift_num: number;
}

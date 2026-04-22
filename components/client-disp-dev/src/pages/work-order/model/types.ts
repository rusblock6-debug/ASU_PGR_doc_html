import type { RouteTaskStatus, TypeTaskValue } from '@/shared/api/endpoints/route-tasks';

import { BlockReason } from './block-reasons';
import { RouteTaskWarningReason } from './warning-reasons';

/**
 * Параметры текущей смены.
 */
export interface CurrentShift {
  /** Дата смены (YYYY-MM-DD). */
  readonly shiftDate: string;
  /** Номер смены. */
  readonly shiftNum: number;
  /** Идентификатор рабочего режима. */
  readonly workRegimeId: number;
}

/**
 * Идентификатор маршрутного задания.
 */
export interface TaskIdentifier {
  /** Идентификатор транспорта. */
  readonly vehicleId: number;
  /** Идентификатор задачи. */
  readonly taskId: string;
}

/**
 * Связанные поля для автоматического пересчёта.
 */
export type LinkedField = keyof Pick<RouteTaskDraft, 'volume' | 'weight' | 'plannedTripsCount'>;

/**
 * Поля маршрутного задания, которые пользователь может редактировать.
 */
export type RouteTaskEditableField = keyof Pick<
  RouteTaskDraft,
  'placeStartId' | 'placeEndId' | 'volume' | 'weight' | 'plannedTripsCount' | 'message' | 'taskType'
>;

/**
 * Редактируемые поля state.modified.
 */
export type RouteTaskEditableFields = Pick<
  RouteTaskDraft,
  'placeStartId' | 'placeEndId' | 'volume' | 'weight' | 'plannedTripsCount' | 'message' | 'taskType'
>;

/**
 * Значение UI-фильтра статуса заданий.
 */
export type StatusFilterValue = 'all' | 'active';

/**
 * Состояние страницы «Наряд-задание».
 */
export interface WorkOrderState {
  /** Параметры текущей смены. */
  readonly currentShift: CurrentShift | null;
  /** Идентификатор выбранных машин для фильтрации (пустой массив = показывать все). */
  readonly selectedVehicleIds: number[];
  /** Фильтр по статусу маршрутных заданий ('all' = без фильтра). */
  readonly selectedStatus: StatusFilterValue;
  /** Новые задания без серверного ID сгруппированные по vehicleId. */
  readonly created: Record<number, Record<string, RouteTaskDraft>>;
  /** Изменения существующих заданий сгруппированные по vehicleId, содержит только измененные поля. */
  readonly modified: Record<number, Record<string, Partial<RouteTaskEditableFields>>>;
  /** Идентификатор серверных заданий для удаления сгруппированные по vehicleId. */
  readonly deleted: Record<number, string[]>;
  /** Ошибки валидации по taskId. */
  readonly validationErrors: Record<string, TaskBlockState>;
  /** Предупреждения валидации по taskId. */
  readonly validationWarnings: Record<string, TaskWarningState>;
  /** Блокировка кнопки отправки после неудачной валидации. */
  readonly isSubmitBlocked: boolean;
}

/**
 * Локальные изменения маршрутных заданий (created/modified/deleted).
 */
export type WorkOrderEdits = Pick<WorkOrderState, 'created' | 'modified' | 'deleted'>;

/**
 * Значение причины блокировки.
 */
export type BlockReasonValue = (typeof BlockReason)[keyof typeof BlockReason];

/**
 * Состояние блокировки/ошибки задания.
 */
export interface TaskBlockState {
  /** Причина блокировки. */
  readonly reason: BlockReasonValue;
  /** Список полей с ошибкой, выделяется в UI красной рамкой. */
  readonly errorFields: readonly RouteTaskEditableField[];
}

/**
 * Значение причины предупреждения.
 */
export type WarningReasonValue = (typeof RouteTaskWarningReason)[keyof typeof RouteTaskWarningReason];

/**
 * Состояние предупреждения задания.
 */
export interface TaskWarningState {
  /** Причина предупреждения. */
  readonly reason: WarningReasonValue;
  /** Список полей с предупреждением, выделяется в UI желтой рамкой. */
  readonly warningFields: readonly RouteTaskEditableField[];
}

/**
 * Маршрутное задание (редактируемое).
 */
export interface RouteTaskDraft {
  /** Идентификатор задачи (серверный или локальный). */
  readonly id: string;
  /** Идентификатор места погрузки. */
  readonly placeStartId: number | null;
  /** Идентификатор места разгрузки. */
  readonly placeEndId: number | null;
  /** Объем груза. */
  readonly volume: number | null;
  /** Вес груза. */
  readonly weight: number | null;
  /** Планируемое количество рейсов. */
  readonly plannedTripsCount: number | null;
  /** Комментарий. */
  readonly message: string | null;
  /** Тип задания. */
  readonly taskType: TypeTaskValue;
  /** Статус задания. */
  readonly status: RouteTaskStatus;
}

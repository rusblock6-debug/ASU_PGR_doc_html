import { RouteStatus, type RouteTaskStatus } from '@/shared/api/endpoints/route-tasks';

import type { RouteTaskEditableField, StatusFilterValue } from './types';

/** Обязательные поля для заполнения. */
export const REQUIRED_FIELDS: RouteTaskEditableField[] = [
  'placeStartId',
  'placeEndId',
  'volume',
  'weight',
  'plannedTripsCount',
  'taskType',
] as const;

/** Статусы, при которых задание «В работе». */
export const ACTIVE_STATUS: ReadonlySet<RouteTaskStatus> = new Set([RouteStatus.ACTIVE]);

/** Маппинг UI-фильтра статуса на RouteTaskStatus[] для API. */
export const STATUS_FILTER_MAP: Readonly<Record<StatusFilterValue, readonly RouteTaskStatus[] | undefined>> = {
  all: undefined,
  active: [...ACTIVE_STATUS],
};

/** Статусы, при которых редактирование задания разрешено. */
export const EDITABLE_STATUSES: ReadonlySet<RouteTaskStatus> = new Set([RouteStatus.EMPTY, RouteStatus.SENT]);

/** Статусы, при которых задание можно отменить. */
export const CANCELLABLE_STATUSES: ReadonlySet<RouteTaskStatus> = new Set([
  RouteStatus.DELIVERED,
  RouteStatus.ACTIVE,
  RouteStatus.PAUSED,
]);

/** Статусы, при которых задание можно назначить. */
export const ASSIGNABLE_STATUSES: ReadonlySet<RouteTaskStatus> = new Set([RouteStatus.DELIVERED]);

/** Статусы, при которых задание можно возобновить. */
export const RESUMABLE_STATUSES: ReadonlySet<RouteTaskStatus> = new Set([RouteStatus.PAUSED]);

import type { VehicleState } from '@/shared/api/types/vehicle-events';

const normalize = (s: string) => s.toUpperCase().replaceAll('-', '_');

/**
 * Человекочитаемый статус движения борта из state_event стрима.
 */
export const getStateEventLabel = (status: VehicleState) => {
  switch (status) {
    case 'idle':
      return 'ПРОСТОЙ';
    case 'moving_empty':
      return 'ДВИЖЕНИЕ ПОРОЖНИМ';
    case 'stopped_empty':
      return 'СТОЯНКА ПОРОЖНИМ';
    case 'loading':
      return 'ПОГРУЗКА';
    case 'moving_loaded':
      return 'ДВИЖЕНИЕ ГРУЖЁНЫМ';
    case 'stopped_loaded':
      return 'СТОЯНКА ГРУЖЁНЫМ';
    case 'unloading':
      return 'РАЗГРУЗКА';
    default:
      return status;
  }
};

/**
 * Человекочитаемый статус маршрутного задания для UI.
 */
export const getRouteStatusLabel = (status: string) => {
  const u = normalize(status);
  switch (u) {
    case 'DELIVERED':
    case 'SENT':
    case 'EMPTY':
      return 'ОЖИДАЕТ';
    case 'ACTIVE':
    case 'IN_PROGRESS':
      return 'В РАБОТЕ';
    case 'PAUSED':
      return 'ПАУЗА';
    case 'REJECTED':
      return 'ОТМЕНЁН';
    case 'COMPLETED':
      return 'ЗАВЕРШЁН';
    default:
      return status;
  }
};

/**
 * CSS-модификатор строки таблицы по статусу.
 */
export const getRouteStatusVariant = (status: string) => {
  const u = normalize(status);
  if (u === 'DELIVERED' || u === 'SENT' || u === 'EMPTY') {
    return 'waiting';
  }
  if (u === 'ACTIVE' || u === 'IN_PROGRESS') {
    return 'active';
  }
  if (u === 'PAUSED') {
    return 'paused';
  }
  if (u === 'REJECTED') {
    return 'cancelled';
  }
  if (u === 'COMPLETED') {
    return 'done';
  }
  return 'default';
};

/** Можно активировать (ожидает / пауза). */
export const isRouteTaskActionable = (status: string) => {
  const u = normalize(status);
  return u === 'DELIVERED' || u === 'SENT' || u === 'EMPTY' || u === 'PAUSED';
};

/** В работе на линии. */
export const isRouteTaskInProgress = (status: string) => {
  const u = normalize(status);
  return u === 'ACTIVE' || u === 'IN_PROGRESS';
};

/** Терминальный статус маршрута. */
export const isRouteTaskFinished = (status: string) => {
  const u = normalize(status);
  return u === 'COMPLETED' || u === 'REJECTED';
};

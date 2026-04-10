import type { StateHistory } from '@/shared/api/endpoints/state-history';

/**
 * Возвращает отображаемое значение источника статуса.
 *
 * @param stateHistory элемент истории статусов.
 */
export function getStatusSourceDisplayName(stateHistory: StateHistory) {
  if (stateHistory.source === 'dispatcher') {
    return 'Диспетчер';
  }

  return 'Система';
}

/**
 * Проверяет, является ли статус концом предыдущего цикла.
 *
 * @param statusCycleId идентификатор цикла редактируемого статуса.
 * @param prevStatusCycleId идентификатор цикла статуса, предшествующего редактируемому статусу.
 */
export function isStatusEndOfPrevCycle(statusCycleId?: string | null, prevStatusCycleId?: string | null) {
  if (!prevStatusCycleId) {
    return false;
  }

  return statusCycleId !== prevStatusCycleId;
}

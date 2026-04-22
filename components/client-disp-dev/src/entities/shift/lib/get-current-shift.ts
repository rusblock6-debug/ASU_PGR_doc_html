import type { ShiftInfo } from '../model/shift-info';

/**
 * Возвращает данные о текущей смене.
 *
 * @param date дата.
 * @param shiftsInfo список с информацией о сменах.
 */
export function getCurrentShift(date: Date, shiftsInfo: readonly ShiftInfo[]) {
  return shiftsInfo.find(
    (item) => item.startTime.getTime() <= date.getTime() && item.endTime.getTime() > date.getTime(),
  );
}

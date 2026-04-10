import { addDays, subDays } from 'date-fns';

import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';

import { getCurrentShift } from './get-current-shift';
import { getShiftsInfo } from './get-shifts-info';

/**
 * Возвращает данные о сменах для выбранной даты.
 *
 * @param date дата.
 * @param shiftDefinitions список смен в режиме работы предприятия.
 */
export function getShiftsByDate(date: Date, shiftDefinitions: readonly ShiftDefinition[]) {
  const shiftsInfo = getShiftsInfo([subDays(date, 1), date, addDays(date, 1)], shiftDefinitions);

  const currentShift = getCurrentShift(date, shiftsInfo);

  return shiftsInfo.filter((item) => item.shiftDate.getTime() === currentShift?.shiftDate.getTime());
}

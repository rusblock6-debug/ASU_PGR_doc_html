import { addDays, subDays } from 'date-fns';

import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';

import { getCurrentShift } from './get-current-shift';
import { getShiftsInfo } from './get-shifts-info';

/**
 * Возвращает данные о смене.
 *
 * @param date дата.
 * @param shiftDefinitions список смен в режиме работы предприятия.
 */
export function getShiftByDate(date: Date, shiftDefinitions: readonly ShiftDefinition[]) {
  const shiftsInfo = getShiftsInfo([subDays(date, 1), date, addDays(date, 1)], shiftDefinitions);

  return getCurrentShift(date, shiftsInfo);
}

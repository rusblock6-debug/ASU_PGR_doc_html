import type { ShiftDefinition } from '@/shared/api/endpoints/work-regimes';

import { MSK_CORRECTION_OFFSET } from '../model/constants';
import type { ShiftInfo } from '../model/shift-info';

/**
 * Возвращает информацию о сменах.
 *
 * @param days список дней для которых необходимо получить информацию о сменах.
 * @param shiftDefinitions список смен в режиме работы предприятия.
 */
export function getShiftsInfo(
  days: readonly Date[],
  shiftDefinitions: readonly ShiftDefinition[],
): readonly ShiftInfo[] {
  const msDates = days.map((day) => Date.UTC(day.getUTCFullYear(), day.getUTCMonth(), day.getUTCDate()));

  return msDates.flatMap((ms) =>
    shiftDefinitions.map(
      (item) =>
        ({
          shiftNum: item.shift_num,
          shiftDate: new Date(ms),
          startTime: new Date(ms + (item.start_time_offset - MSK_CORRECTION_OFFSET) * 1000),
          endTime: new Date(ms + (item.end_time_offset - MSK_CORRECTION_OFFSET) * 1000),
        }) satisfies ShiftInfo,
    ),
  );
}

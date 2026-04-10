import { MIN_TRIP_DURATION } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';

/**
 * Проверяет, что продолжительность статуса достаточна для создания внутри него рейса.
 *
 * @param startDate дата начала статуса.
 * @param endDate дата окончания статуса.
 */
export function isValidStatusDurationToAddTrip(startDate: string, endDate?: string) {
  const cycleStartedAt = new Date(startDate).getTime();
  const cycleCompletedAt = hasValue(endDate) ? new Date(endDate).getTime() : new Date().getTime();

  if (cycleCompletedAt > 0 && cycleStartedAt > 0) {
    const cycleDuration = cycleCompletedAt - cycleStartedAt;

    if (cycleDuration < MIN_TRIP_DURATION) {
      return false;
    }
  }

  return true;
}

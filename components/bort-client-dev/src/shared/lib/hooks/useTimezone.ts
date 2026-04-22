import { createTimezoneFormatter } from '../timezone';

/** Возвращает форматтер московского времени. */
export function useTimezone() {
  const timezone = 'Europe/Moscow';

  return createTimezoneFormatter(timezone);
}

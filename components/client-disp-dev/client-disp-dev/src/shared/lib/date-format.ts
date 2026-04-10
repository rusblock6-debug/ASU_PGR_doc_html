import { format as dateFnsFormat, isValid } from 'date-fns';

/**
 * Преобразует строку формата "Tue, 04 Nov 2025 00:00:00 GMT" в "2025-11-04".
 *
 * @param dateString Строка для преобразования.
 */
export function dateTimeStringToDateString(dateString: string): string {
  const date = new Date(dateString);

  if (!isValid(date)) {
    throw new Error('Invalid date string');
  }

  return dateFnsFormat(date, 'yyyy-MM-dd');
}

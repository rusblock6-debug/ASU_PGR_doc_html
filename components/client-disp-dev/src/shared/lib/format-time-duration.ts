import { hasValueNotEmpty } from '@/shared/lib/has-value';

/**
 * Вычисляет продолжительность.
 *
 * @param start время начала.
 * @param end время окончания.
 * @returns продолжительность в миллисекундах.
 */
export function calculateDuration(start: Date | string, end: Date | string) {
  const startDate = new Date(start);
  const endDate = new Date(end);

  return endDate.getTime() - startDate.getTime();
}

/**
 * Возвращает отображаемое значение продолжительности времени в формате "1 д. 5 ч. 42 мин. 15 сек."
 *
 * @param duration продолжительность в миллисекундах.
 */
export function getTimeDurationDisplayValue(duration: number) {
  if (duration < 0) return 'Некорректные даты';
  if (duration === 0) return '0 мин.';

  const totalSeconds = Math.floor(duration / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const parts = [
    days > 0 ? `${days} д.` : '',
    hours > 0 ? `${hours} ч.` : '',
    minutes > 0 ? `${minutes} мин.` : '',
    seconds > 0 || (days === 0 && hours === 0 && minutes === 0) ? `${seconds} сек.` : '',
  ].filter(hasValueNotEmpty);

  return parts.join(' ');
}

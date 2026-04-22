/**
 * Форматирует расстояние в метрах в строку с километрами и метрами.
 *
 * Если расстояние больше или равно 1000 м, километры и остаток метров
 * отображаются отдельно. Нулевые значения не выводятся.
 *
 * @example
 * formatDistance(3200) // '3 км 200 м'
 * formatDistance(1000) // '1 км'
 * formatDistance(250) // '250 м'
 * formatDistance(0) // '0 м'
 *
 * @param value Расстояние в метрах.
 * @returns Отформатированная строка расстояния.
 */
export function formatDistance(value: number) {
  const km = Math.floor(value / 1000);
  const m = value % 1000;

  const parts = [];

  if (km) parts.push(`${km} км`);
  if (m) parts.push(`${m} м`);

  return parts.join(' ') || '0 м';
}

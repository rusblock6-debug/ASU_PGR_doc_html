import { hasValue, hasValueNotEmpty } from './has-value';

const numberFormatter = new Intl.NumberFormat('ru-RU');

/**
 * Конвертирует переданное значение в значение типа 'number' или возвращает 'null' если конвертация невозможна.
 *
 * @param value конвертируемое значение.
 */
export function convertToNumberOrNull(value?: unknown) {
  if (!hasValueNotEmpty(value)) {
    return null;
  }

  const num = typeof value === 'number' ? value : Number(value);

  return isNaN(num) ? null : num;
}

/**
 * Форматирует число в русской локали с разделителем тысяч.
 *
 * @example
 * formatNumber(1000) // '1 000'
 * formatNumber(1234.56) // '1 234,56'
 * formatNumber('123') // '123'
 * formatNumber('') // ''
 * formatNumber(null) // ''
 *
 * @param value Число, строка или произвольное значение для приведения к числу.
 * @returns Отформатированная строка или пустая строка если значение невалидно.
 */
export function formatNumber(value?: unknown) {
  const num = convertToNumberOrNull(value);

  return hasValue(num) ? numberFormatter.format(num) : '';
}

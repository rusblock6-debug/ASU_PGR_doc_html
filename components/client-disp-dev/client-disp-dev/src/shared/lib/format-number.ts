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
 * @param emptyValue Пустое значение.
 * @returns Отформатированная строка или пустая строка если значение невалидно.
 */
export function formatNumber(value?: unknown, emptyValue = '') {
  const num = convertToNumberOrNull(value);

  return hasValue(num) ? numberFormatter.format(num) : emptyValue;
}

/**
 * Округляет число до одного знака после запятой.
 *
 * @example
 * roundToFixed(1.56) // 1.6
 * roundToFixed(2.34) // 2.3
 * roundToFixed(5)    // 5
 *
 * @param value Число для округления.
 * @returns Число, округлённое до одного десятичного знака.
 */
export const roundToFixed = (value: number) => Math.round(value * 10) / 10;

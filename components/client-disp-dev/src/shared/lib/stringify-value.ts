/**
 * Безопасно преобразует `unknown` в строку без риска получить `[object Object]`.
 *
 * @param value Произвольное значение.
 * @returns Строковое представление значения или пустая строка для null/undefined.
 */
export function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return '';

  switch (typeof value) {
    case 'string':
      return value;
    case 'number':
    case 'boolean':
    case 'bigint':
      return String(value);
    case 'object': {
      if (value instanceof Date) return value.toISOString();
      if (Array.isArray(value)) return value.map(stringifyValue).join(' ');
      try {
        return JSON.stringify(value);
      } catch {
        return '';
      }
    }
    default:
      return '';
  }
}

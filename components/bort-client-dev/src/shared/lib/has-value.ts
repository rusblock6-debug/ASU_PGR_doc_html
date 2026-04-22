/**
 * Возвращает true, если значение не равно null или undefined.
 *
 * @param value Проверяемое значение.
 */
export function hasValue<TValue>(value: TValue | null | undefined): value is TValue {
  return value !== null && value !== undefined;
}

/**
 * Возвращает true, если значение не равно null, undefined или ''.
 *
 * @param value Проверяемое значение.
 */
export function hasValueNotEmpty<T = string>(value: T | undefined | null | ''): value is T {
  return hasValue(value) && value !== '';
}

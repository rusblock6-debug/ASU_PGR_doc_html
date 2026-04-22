import { hasValue, hasValueNotEmpty } from './has-value';

/**
 * Проверяет, имеет ли значение параметр {@link value}.
 * Сужает тип {@link value} до гарантированно имеющего значение.
 *
 * @param value Проверяемое значение.
 * @param message Сообщение.
 */
export function assertHasValue<T>(value: T | undefined | null, message?: string): asserts value is T {
  if (!hasValue(value)) {
    throw new Error(message ?? 'Значение должно быть определено');
  }
}

/**
 * Проверяет, имеет ли значение параметр {@link value} функцией {@link hasValueNotEmpty}.
 * Сужает тип {@link value} до гарантированно имеющего значение.
 *
 * @param value Проверяемое значение.
 * @param message Сообщение.
 */
export function assertHasValueNotEmpty<T>(value: T | undefined | null | '', message?: string): asserts value is T {
  if (!hasValueNotEmpty(value)) {
    throw new Error(message ?? 'Значение должно быть определено и не должно являться пустой строкой');
  }
}

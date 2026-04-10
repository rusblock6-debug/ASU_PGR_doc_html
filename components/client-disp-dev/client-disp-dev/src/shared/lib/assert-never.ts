/**
 * Утверждает, что переданное значение никогда не должно быть достигнуто.
 * Генерирует исключение компиляции в случае если передано значение отличное от never.
 */
export function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}

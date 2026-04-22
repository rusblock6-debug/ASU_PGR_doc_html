/**
 * Убирает readonly модификаторы для всех полей.
 */
export type Writable<T> = { -readonly [P in keyof T]: T[P] };

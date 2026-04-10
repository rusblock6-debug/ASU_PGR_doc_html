/**
 * Типобезопасная версия `Object.entries`.
 *
 * В отличие от стандартного `Object.entries`, который возвращает
 * `[string, any][]`, эта функция сохраняет реальные типы ключей и значений объекта:
 *
 * - ключ → `keyof T`
 * - значение → `T[keyof T]`
 *
 * @param obj объект, для которого нужно получить пары [key, value]
 * @returns массив типобезопасных пар [ключ, значение]
 */
export function typedEntries<T extends object>(obj: T) {
  return Object.entries(obj) as [keyof T, T[keyof T]][];
}

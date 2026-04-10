/**
 * Группирует массив по указанному полю. Возвращает структуру типа "Map".
 *
 * @param items список элементов для группировки.
 * @param fieldName имя поля элемента.
 */
export function getMapGroupedByField<T, K extends keyof T>(items: readonly T[], fieldName: K): Map<T[K], readonly T[]> {
  const map = new Map<T[K], T[]>();

  for (const cur of items) {
    const groupName = cur[fieldName];
    const group = map.get(groupName);

    if (group) {
      group.push(cur);
    } else {
      map.set(groupName, [cur]);
    }
  }

  return map;
}

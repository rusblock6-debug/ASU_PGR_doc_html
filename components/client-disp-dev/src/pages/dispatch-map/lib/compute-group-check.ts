/**
 * Вычисляет видимость группы элементов.
 */
export function computeGroupCheck(itemIds: readonly number[], selectedIds: readonly number[]) {
  if (itemIds.length === 0) return false;

  return itemIds.every((id) => selectedIds.includes(id));
}

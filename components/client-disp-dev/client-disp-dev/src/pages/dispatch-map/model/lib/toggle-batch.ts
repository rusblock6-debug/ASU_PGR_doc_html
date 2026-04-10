/**
 * Переключает видимость группы элементов:
 * если все `ids` видимы, скрываем их (добавляем в `hiddenIds`);
 * иначе — показываем все (убираем из `hiddenIds`).
 */
export function toggleBatch(hiddenIds: readonly number[], ids: readonly number[]) {
  const allVisible = ids.every((id) => !hiddenIds.includes(id));
  if (allVisible) {
    return [...hiddenIds, ...ids];
  }
  return hiddenIds.filter((id) => !ids.includes(id));
}

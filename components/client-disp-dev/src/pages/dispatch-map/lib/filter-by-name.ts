/**
 * Фильтрует массив по подстроке в поле `name` (не зависит от регистра).
 * Если строка поиска пуста — возвращает исходный массив без копирования.
 */
export function filterByName<T extends { readonly name: string }>(items: readonly T[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (normalized.length === 0) return items;

  return items.filter((item) => item.name.toLowerCase().includes(normalized));
}

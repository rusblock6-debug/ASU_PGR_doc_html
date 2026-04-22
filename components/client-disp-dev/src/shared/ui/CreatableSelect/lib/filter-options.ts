import { hasValueNotEmpty } from '@/shared/lib/has-value';
import type { SelectOption } from '@/shared/ui/types';

/** Фильтрует опции по поисковому запросу */
export function filterOptions<T extends SelectOption>(options: readonly T[], search: string) {
  const searchLower = search.toLowerCase().trim();
  if (!hasValueNotEmpty(searchLower)) return options;
  return options.filter((option) => option.label.toLowerCase().trim().includes(searchLower));
}

const DEFAULT_DELAY = 300;
const DEFAULT_PAGINATED_LIST_SIZE = 1000;
const DEFAULT_DICTIONARY_SIZE = 99;

function getFromLocalStorage(key: string, defaultValue: number): number {
  if (typeof window === 'undefined') return defaultValue;
  const stored = localStorage.getItem(key);
  return stored ? Number(stored) : defaultValue;
}

/**
 * Конфигурация MSW моков.
 * Можно переопределить через localStorage (применяется сразу, без перезагрузки):
 *
 * ```js
 * localStorage.setItem('msw_delay', '1000')
 * localStorage.setItem('msw_paginated_list_size', '2000')
 * localStorage.setItem('msw_dictionary_size', '50')
 * ```
 */
export const mswConfig = {
  /** Задержка ответа в миллисекундах. */
  get delay() {
    return getFromLocalStorage('msw_delay', DEFAULT_DELAY);
  },

  /** Размер датасета для списков с пагинацией/infinite scroll. */
  get paginatedListSize() {
    return getFromLocalStorage('msw_paginated_list_size', DEFAULT_PAGINATED_LIST_SIZE);
  },

  /** Размер датасета для справочников. */
  get dictionarySize() {
    return getFromLocalStorage('msw_dictionary_size', DEFAULT_DICTIONARY_SIZE);
  },
};

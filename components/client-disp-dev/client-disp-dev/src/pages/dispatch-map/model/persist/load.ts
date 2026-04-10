import { hasValue } from '@/shared/lib/has-value';

import type { PersistFieldConfig } from './types';

/**
 * Загружает значение поля из LocalStorage.
 * При отсутствии данных или ошибке парсинга возвращает дефолтное значение.
 */
export function loadPersistedField<T>(config: PersistFieldConfig<T>): T {
  try {
    const raw = localStorage.getItem(config.key);
    return hasValue(raw) ? (JSON.parse(raw) as T) : config.defaultValue;
  } catch {
    return config.defaultValue;
  }
}

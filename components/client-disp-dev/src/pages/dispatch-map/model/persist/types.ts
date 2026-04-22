import type { MapState } from '../types';

/** Минимальный конфиг для отслеживания и сохранения изменений поля. */
export interface PersistSyncConfig {
  /** Ключ в LocalStorage. */
  readonly key: string;
  /** Селектор поля из слайса карты. */
  readonly selector: (state: MapState) => unknown;
}

/** Полный конфиг персистентности одного поля слайса карты. */
export interface PersistFieldConfig<T> {
  /** Ключ в LocalStorage. */
  readonly key: string;
  /** Селектор поля из слайса карты. */
  readonly selector: (state: MapState) => T;
  /** Значение по умолчанию при отсутствии или повреждении данных. */
  readonly defaultValue: Readonly<T>;
}

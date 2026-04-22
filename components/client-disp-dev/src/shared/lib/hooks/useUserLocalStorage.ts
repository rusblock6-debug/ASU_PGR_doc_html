import { type Dispatch, type SetStateAction, useCallback, useMemo, useRef, useSyncExternalStore } from 'react';

import { hasValue } from '@/shared/lib/has-value';
import { toast } from '@/shared/ui/Toast';

import { useUserGeneratedKey } from './useUserGeneratedKey';

type LocalStorageState<T> = [T, Dispatch<SetStateAction<T>>, () => void];

/**
 * Используется для хранения данных в тех случаях, когда данные не могут быть успешно сохранены в localStorage.
 */
const inMemoryData = new Map<string, unknown>();

const callbacks = new Set<(key: string) => void>();

/**
 * Используется для сохранения и извлечения состояние из LocalStorage для авторизованного пользователя.
 *
 * @param baseKey Ключ для хранения значения в LocalStorage.
 * @param defaultValue  Значение по умолчанию, которое будет использовано, если данных в LocalStorage нет.
 */
export function useUserLocalStorage<T = undefined>(baseKey: string, defaultValue: T): LocalStorageState<T> {
  const key = useUserGeneratedKey(baseKey);
  const storageItem = useRef<{ storedString: string | null; parsed: T }>({
    storedString: null,
    parsed: defaultValue,
  });
  const value = useSyncExternalStore(
    useCallback(
      (onStoreChange) => {
        if (!hasValue(key)) {
          return () => undefined;
        }
        const onChange = (localKey: string): void => {
          if (key === localKey) {
            onStoreChange();
          }
        };
        callbacks.add(onChange);
        return (): void => {
          callbacks.delete(onChange);
        };
      },
      [key],
    ),
    () => {
      if (!hasValue(key)) {
        return defaultValue;
      }
      const fetchedString = catchExceptions(() => localStorage.getItem(key)) ?? null;
      if (inMemoryData.has(key)) {
        storageItem.current.parsed = inMemoryData.get(key) as T;
      } else if (fetchedString !== storageItem.current.storedString) {
        let parsed: T | undefined;

        try {
          parsed = fetchedString === null ? defaultValue : (JSON.parse(fetchedString) as T);
        } catch {
          parsed = defaultValue;
        }

        storageItem.current.parsed = parsed;
      }

      storageItem.current.storedString = fetchedString;
      return storageItem.current.parsed;
    },
    () => defaultValue,
  );

  const setState = useCallback(
    (newValue: React.SetStateAction<T>): void => {
      if (!hasValue(key)) {
        return;
      }
      const valueToSet = newValue instanceof Function ? newValue(storageItem.current.parsed) : newValue;
      try {
        const stringValue = JSON.stringify(valueToSet);
        localStorage.setItem(key, stringValue);
        inMemoryData.delete(key);
      } catch {
        inMemoryData.set(key, valueToSet);
      }

      triggerCallbacks(key);
    },
    [key],
  );

  const removeItem = useCallback((): void => {
    if (!hasValue(key)) {
      return;
    }
    catchExceptions(() => localStorage.removeItem(key));
    inMemoryData.delete(key);
    triggerCallbacks(key);
  }, [key]);

  return useMemo(() => [value, setState, removeItem], [setState, value, removeItem]);
}

/**
 * Функция вызова колбэков.
 *
 * @param key ключ.
 */
function triggerCallbacks(key: string): void {
  callbacks.forEach((callback) => {
    callback(key);
  });
}

/**
 * Безопасно выполняет функцию, обрабатывая возможные исключения.
 *
 * @param tryFn Функция для выполнения.
 */
function catchExceptions<T>(tryFn: () => T): T | undefined {
  try {
    return tryFn();
  } catch {
    toast.error({ message: 'Ошибка при работе с localStorage' });
    return undefined;
  }
}

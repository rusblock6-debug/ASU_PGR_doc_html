import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';

type ClassNamesRecord = Record<string, string | undefined>;

/**
 * Мержит несколько объектов classNames для Mantine компонентов.
 * Одноимённые ключи склеиваются через `cn()`, а не перезаписываются.
 *
 * @example
 * // В адаптере TextInput:
 * classNames={mergeMantineClassNames(
 *   mantineInput,       // базовые стили из shared/styles/mantine
 *   mantineInputWrapper,
 *   { input: styles.input },  // локальные стили адаптера
 *   classNamesObj       // пользовательские стили (из props)
 * )}
 *
 * @param sources объекты classNames для мерджа (null/undefined пропускаются)
 * @returns объединённый объект classNames
 */
export function mergeMantineClassNames(...sources: (ClassNamesRecord | null | undefined)[]) {
  const result: ClassNamesRecord = {};

  for (const source of sources) {
    if (!hasValue(source)) continue;

    for (const [key, value] of Object.entries(source)) {
      if (!hasValue(value)) continue;

      if (result[key]) {
        result[key] = cn(result[key], value);
      } else {
        result[key] = value;
      }
    }
  }

  return result;
}

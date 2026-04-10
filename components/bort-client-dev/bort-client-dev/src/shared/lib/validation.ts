import { z } from 'zod';

import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';

const EMPTY_COORDINATES = { lat: null, lon: null } as const;

/**
 * Базовая строковая валидация для обязательных полей.
 */
export const STRING_VALIDATION = z.string({ message: 'Заполните поле' }).trim().min(1, { message: 'Заполните поле' });

/**
 * Валидация для значения (value) выпадающего списка.
 * Принимает строку (непустую), число (любое, включая 0) или boolean,
 * потому что SelectField преобразует значение обратно в нужный тип на основе valueType из meta.
 */
export const SELECT_VALIDATION = z.union([STRING_VALIDATION, z.number(), z.boolean()], {
  message: 'Заполните поле',
});

/**
 * Валидация полей даты/времени.
 * Принимает строку или объект Date.
 */
export const DATE_VALIDATION = createValidation(z.date({ message: 'Должна быть валидная дата' }));

/**
 * Валидация необязательных числовых полей.
 */
export const NUMBER_OPTIONAL_VALIDATION = z.union([z.string(), z.number()]).optional().nullable();

/**
 * Валидация числовых полей.
 */
export const NUMBER_VALIDATION = createValidation(z.number({ message: 'Должно быть числом' }));

/**
 * Валидация числовых полей, значение которых должно быть больше или равно 0.
 */
export const ZERO_POSITIVE_NUMBER_VALIDATION = createValidation(
  z.number({ message: 'Должно быть числом' }).nonnegative({ message: 'Число не может быть отрицательным' }),
);

/**
 * Валидация числовых полей, значение которых должно быть строго больше 0.
 */
export const POSITIVE_NUMBER_VALIDATION = createValidation(
  z.number({ message: 'Должно быть числом' }).positive({ message: 'Число должно быть больше 0' }),
);

/**
 * Валидация мультикатегории (массив строк или чисел).
 */
export const MULTI_CATEGORY_VALIDATION = z.array(z.string()).nonempty({ message: 'Заполните поле' });

/**
 * Валидация времени в формате ISO (HH:mm).
 */
export const TIME_VALIDATION = z.iso.time({ precision: -1, message: 'Неверный формат времени (HH:mm)' });

/**
 * Схема валидации для координат.
 * Нельзя заполнить только одно поле — оба должны быть заполнены или оба пусты.
 */
export function createCoordinatesSchema(required: boolean) {
  const numberSchema = z
    .number({ message: 'Заполните поле' })
    .nonnegative({ message: 'Число не может быть отрицательным' });

  // Преобразуем null/'' в undefined, затем применяем схему (optional для необязательных полей)
  const fieldSchema = required ? numberSchema : numberSchema.optional();
  const coordinatesSchema = z.preprocess((val) => (hasValueNotEmpty(val) ? val : undefined), fieldSchema);

  const objectSchema = z.object({ lat: coordinatesSchema, lon: coordinatesSchema }).superRefine((data, ctx) => {
    const hasLat = hasValueNotEmpty(data.lat);
    const hasLon = hasValueNotEmpty(data.lon);

    if (hasLat && !hasLon) {
      ctx.addIssue({ code: 'custom', message: 'Заполните долготу', path: ['lon'] });
    }
    if (hasLon && !hasLat) {
      ctx.addIssue({ code: 'custom', message: 'Заполните широту', path: ['lat'] });
    }
  });

  // Преобразуем null объект в пустые координаты
  return z.preprocess((val) => (hasValue(val) ? val : EMPTY_COORDINATES), objectSchema);
}

/**
 * Функция для создания валидации с поддержкой обязательности заполнения.
 * Возвращает функцию, которая принимает `required` и возвращает схему или её опциональную версию.
 */
export function withRequired<T extends z.ZodType>(schema: T) {
  // Преобразует пустые значения в undefined, чтобы необязательные поля можно было оставить пустыми
  const toUndefinedIfEmpty = (val: unknown) => (hasValueNotEmpty(val) ? val : undefined);

  return (required: boolean) => (required ? schema : z.preprocess(toUndefinedIfEmpty, schema.optional()));
}

/**
 * Функция для создания валидации с поддержкой строкового ввода.
 * Принимает любую Zod-схему и объединяет её с requiredString.
 */
function createValidation<T extends z.ZodType>(schema: T) {
  return z.union([STRING_VALIDATION, schema]);
}

/**
 * Функция для валидации нескольких полей с датами.
 * Проверяет, что значение находится в заданном диапазоне относительно других полей.
 */
export function validateDateRange(config: {
  /** Поле с минимальным значением (текущее должно быть >= min). */
  readonly min?: { readonly field: string; readonly message?: string };
  /** Поле с максимальным значением (текущее должно быть <= max). */
  readonly max?: { readonly field: string; readonly message?: string };
}) {
  return (value: unknown, formData: Record<string, unknown>) => {
    if (!hasValue(value)) return;

    const current = new Date(value as string).getTime();

    if (config.min && hasValue(formData[config.min.field])) {
      const min = new Date(formData[config.min.field] as string).getTime();
      if (current < min) {
        return config.min.message ?? 'Значение не может быть раньше связанного поля';
      }
    }

    if (config.max && hasValue(formData[config.max.field])) {
      const max = new Date(formData[config.max.field] as string).getTime();
      if (current > max) {
        return config.max.message ?? 'Значение не может быть позже связанного поля';
      }
    }
  };
}

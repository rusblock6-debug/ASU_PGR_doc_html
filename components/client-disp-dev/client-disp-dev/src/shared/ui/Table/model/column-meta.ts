import type { HTMLInputTypeAttribute } from 'react';
import type { z } from 'zod';

import type { SelectOption } from '@/shared/ui/types';

import { ColumnDataTypes } from '../types';

/**
 * Тип значения для выпадающего списка.
 * Определяет, в какой тип будет преобразовано строковое значение при onChange.
 */
export type SelectValueType = 'string' | 'number' | 'boolean';

/** Общие поля для всех типов ColumnDataTypes. */
interface BaseColumnMeta {
  /** Определяет поле только для чтения. */
  readonly readOnly?: boolean;
  /** Определяет поле только для чтения в режиме редактирования. */
  readonly readOnlyEdit?: boolean;
  /** Скрывать поле при создании новой записи. */
  readonly hideOnCreate?: boolean;
  /**
   * Выравнивание содержимого ячейки.
   *
   * @default «right» для ColumnDataTypes.NUMBER, ColumnDataTypes.DATE, ColumnDataTypes.DATETIME, ColumnDataTypes.TIME; «left» для остальных
   */
  readonly align?: 'left' | 'right';
  /** Флаг dummy-элемента (используется для визуальных разделителей и т.п.). */
  readonly dummyElement?: boolean;
  /** Флаг кастомной ячейки. Установить `true` если в cell рендерится кастомный компонент. */
  readonly isCustomCell?: boolean;
  /**
   * Обязательность поля для валидации.
   *
   * @default true
   */
  readonly required?: boolean;
  /** Схема кастомной валидации Zod. Без заполнения используется дефолтная валидация из `form-field-registry.ts`. */
  readonly validation?: z.ZodType;
  /** Кросс-валидация для нескольких полей формы. */
  readonly crossValidate?: (value: unknown, formData: Record<string, unknown>) => string | undefined | null;
  /** Признак отображения стандартного 'title' вместо 'Tooltip'. */
  readonly showTitle?: boolean;
}

/**
 * Мета-информация колонки таблицы.
 * Тип определяется полем `dataType` — от него зависят доступные поля и компоненты формы/таблицы.
 */
export type StrictColumnMeta =
  | SelectMeta
  | MultiSelectMeta
  | EditableSelectMeta
  | DateMeta
  | TextMeta
  | AutocompleteTextMeta
  | SimpleMeta;

/** Общие поля выпадающих списков. */
type BaseSelectMeta = BaseColumnMeta & {
  /** Опции для выбора. */
  readonly options: readonly SelectOption[];
  /**
   * Тип значения (value) выпадающего списка.
   * Выпадающий список всегда работает со строками, но при выборе другого пункта — значение (value) будет преобразовано в указанный тип {@link SelectValueType}.
   */
  readonly valueType: SelectValueType;
  /**
   * Автозаполнение других полей формы при выборе значения в выпадающем списке.
   *
   * При выборе опции автоматически заполняются указанные поля соответствующими значениями.
   * При сбросе выбора — зависимые поля сбрасываются в null.
   * Полезно для каскадных зависимостей: например, при выборе модели техники —
   * автоматически подставляются её характеристики (объём, грузоподъёмность и т.д.).
   *
   * @example
   * // При выборе модели с id=1 заполнятся поля volume_m3 и max_speed
   * autoFill: {
   *   '1': { volume_m3: 10, max_speed: 80 },
   *   '2': { volume_m3: 15, max_speed: 60 },
   * }
   */
  readonly autoFill?: Readonly<Record<string, Record<string, unknown>>>;
};

/** Meta для ColumnDataTypes.SELECT колонки. */
export type SelectMeta = BaseSelectMeta & {
  /** Тип данных колонки. */
  readonly dataType: typeof ColumnDataTypes.SELECT;
};

/** Meta для ColumnDataTypes.EDITABLE_SELECT колонки. */
export type EditableSelectMeta = BaseSelectMeta & {
  /** Тип данных колонки. */
  readonly dataType: typeof ColumnDataTypes.EDITABLE_SELECT;
  /** Обработчики для CRUD операций. */
  readonly handlers: EditableSelectHandlers;
};

/** Meta для ColumnDataTypes.MULTI_SELECT колонки. */
export type MultiSelectMeta = BaseColumnMeta & {
  /** Тип данных колонки. */
  readonly dataType: typeof ColumnDataTypes.MULTI_SELECT;
  /** Опции для выбора. */
  readonly options: readonly SelectOption[];
  /** Обработчики для CRUD операций. */
  readonly handlers?: EditableSelectHandlers;
};

/** Meta для ColumnDataTypes.DATE и ColumnDataTypes.DATETIME колонок. */
export type DateMeta = BaseColumnMeta & {
  /** Тип данных колонки. */
  readonly dataType: typeof ColumnDataTypes.DATE | typeof ColumnDataTypes.DATETIME;
  /** Колонка с минимальным значением (для UI-ограничения DateInput). */
  readonly columnWithMinValue?: string;
  /** Колонка с максимальным значением (для UI-ограничения DateInput). */
  readonly columnWithMaxValue?: string;
  /** Возвращает свойства для связанной автоматически заполняемой колонки. */
};

/** Meta для ColumnDataTypes.TEXT колонки. */
export type TextMeta = BaseColumnMeta & {
  /** Тип данных колонки.*/
  readonly dataType?: typeof ColumnDataTypes.TEXT;
  /** Маска ввода. Пока поддерживает только маску для MAC-адреса */
  readonly mask?: 'mac-address';
  /** Тип поля ввода. */
  readonly inputType?: HTMLInputTypeAttribute;
};

/** Meta для ColumnDataTypes.TEXT колонки. */
export type AutocompleteTextMeta = BaseColumnMeta & {
  /** Тип данных колонки.*/
  readonly dataType?: typeof ColumnDataTypes.AUTOCOMPLETE_TEXT;
  /** Опции для выбора. */
  readonly options: readonly string[];
};

/** Обработчики для CRUD операций с ColumnDataTypes.EDITABLE_SELECT полями */
export interface EditableSelectHandlers<T extends SelectOption = SelectOption> {
  /** Создание новой записи. Возвращает созданную опцию. */
  readonly onCreate: (label: string) => Promise<T>;
  /** Редактирование записи. */
  readonly onEdit?: (value: string, newLabel: string) => Promise<T | void>;
  /** Удаление записи. Возвращает `true` если удаление выполнено, `false` если отменено. */
  readonly onDelete?: (value: string) => Promise<boolean>;
}

/** Meta для простых типов без специфичных полей. */
type SimpleMeta = BaseColumnMeta & {
  /** Тип данных колонки. Если не указан, используется ColumnDataTypes.TEXT по умолчанию. */
  readonly dataType?:
    | typeof ColumnDataTypes.NUMBER
    | typeof ColumnDataTypes.TIME
    | typeof ColumnDataTypes.COLOR
    | typeof ColumnDataTypes.COORDINATES
    | typeof ColumnDataTypes.PASSWORD;
};

import type { Cell, Column, Header } from '@tanstack/react-table';

import type {
  AutocompleteTextMeta,
  DateMeta,
  EditableSelectMeta,
  MultiSelectMeta,
  SelectMeta,
  StrictColumnMeta,
  TextMeta,
} from '../model/column-meta';
import { ColumnDataTypes, type ColumnDef } from '../types';

/**
 * Получает значение колонки из данных.
 * Приоритет: accessorKey (если ключ существует в данных) → accessorFn (для вложенных объектов).
 */
export function getColumnValue<TData>(column: ColumnDef<TData>, data: TData) {
  // accessorKey — приоритет для формы
  if ('accessorKey' in column && column.accessorKey) {
    const key = column.accessorKey as string;

    // Если ключ существует в данных — используем его (даже если null)
    if (key in (data as object)) {
      return (data as Record<string, unknown>)[key];
    }
  }

  // Иначе пробуем accessorFn для вложенных объектов (например model?.volume_m3)
  if ('accessorFn' in column && typeof column.accessorFn === 'function') {
    return column.accessorFn(data, 0);
  }

  return undefined;
}

/** Проверяет обязательность колонки. По умолчанию колонка обязательна (required !== false). */
export const isColumnRequired = (meta?: StrictColumnMeta) => {
  return meta?.required !== false;
};

/** Получить типизированную meta из TanStack Column/Cell/Header. */
export function getColumnMeta<TData>(source: Column<TData> | Cell<TData, unknown> | Header<TData, unknown>) {
  const columnDef = 'column' in source ? source.column.columnDef : source.columnDef;
  return columnDef.meta as StrictColumnMeta | undefined;
}

/** Проверяет, является ли meta датой. */
export function isDateMeta(meta?: StrictColumnMeta): meta is DateMeta {
  return meta?.dataType === ColumnDataTypes.DATE || meta?.dataType === ColumnDataTypes.DATETIME;
}

/** Проверяет, является ли meta выпадающим списком с данными. */
export function isSelectMeta(meta?: StrictColumnMeta): meta is SelectMeta {
  return meta?.dataType === ColumnDataTypes.SELECT;
}

/** Проверяет, является ли meta выпадающим списком с множественным выбором. */
export function isMultiSelectMeta(meta?: StrictColumnMeta): meta is MultiSelectMeta {
  return meta?.dataType === ColumnDataTypes.MULTI_SELECT;
}

/** Проверяет, является ли meta выпадающим списком с возможностью редактирования. */
export function isEditableSelectMeta(meta?: StrictColumnMeta): meta is EditableSelectMeta {
  return meta?.dataType === ColumnDataTypes.EDITABLE_SELECT;
}

/** Проверяет, является ли meta текстовым типом. */
export function isTextMeta(meta?: StrictColumnMeta): meta is TextMeta {
  return meta?.dataType === ColumnDataTypes.TEXT;
}

/** Проверяет, является ли meta текстовым типом с предлагаемыми значениями. */
export function isAutocompleteTextMeta(meta?: StrictColumnMeta): meta is AutocompleteTextMeta {
  return meta?.dataType === ColumnDataTypes.AUTOCOMPLETE_TEXT;
}

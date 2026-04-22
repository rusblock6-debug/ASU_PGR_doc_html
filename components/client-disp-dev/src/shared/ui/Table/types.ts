import type { ColumnDef as TanStackColumnDef } from '@tanstack/react-table';
import type React from 'react';

import type { StrictColumnMeta } from './model/column-meta';

export const ColumnDataTypes = {
  TEXT: 'text',
  AUTOCOMPLETE_TEXT: 'autocomplete_text',
  NUMBER: 'number',
  DATE: 'date',
  DATETIME: 'datetime',
  TIME: 'time',
  SELECT: 'select',
  MULTI_SELECT: 'multi_select',
  EDITABLE_SELECT: 'editable_select',
  COORDINATES: 'coordinates',
  COLOR: 'color',
  // eslint-disable-next-line sonarjs/no-hardcoded-passwords
  PASSWORD: 'password',
} as const;

export type ColumnDataType = (typeof ColumnDataTypes)[keyof typeof ColumnDataTypes];

/**
 * Определение колонки таблицы.
 * Расширяет TanStack ColumnDef типизированным meta для настройки поведения формы и ячейки.
 */
export type ColumnDef<TData> = TanStackColumnDef<TData> & {
  /** Мета-информация колонки (тип данных, валидация, опции и т.д.). */
  meta?: StrictColumnMeta;
};

/**
 * Тип колонки для использования в форме.
 * Содержит только свойства, необходимые для рендеринга полей.
 * Не зависит от TData — позволяет избежать type assertion.
 */
export interface FormColumnDef {
  /** Ключ для доступа к значению в объекте данных. */
  readonly accessorKey?: string | number | symbol;
  /** Заголовок колонки для отображения в форме. */
  readonly header?: unknown;
  /** Мета-информация колонки. */
  readonly meta?: StrictColumnMeta;
}

/** Пропсы компонента поля формы. */
export interface FormFieldProps {
  /** Определение колонки с мета-информацией о типе поля. */
  readonly column: FormColumnDef;
  /** Режим формы: 'add' для создания, 'edit' для редактирования. */
  readonly mode: 'add' | 'edit';
}

/** Тип компонента поля формы (TextField, NumberField и т.д.). */
export type FieldComponent = React.FC<FormFieldProps>;

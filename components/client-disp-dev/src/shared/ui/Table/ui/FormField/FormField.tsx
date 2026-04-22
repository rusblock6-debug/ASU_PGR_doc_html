import { getFieldComponent } from '../../config/form-field-registry';
import { ColumnDataTypes, type FormFieldProps } from '../../types';

/**
 * Универсальный компонент поля формы таблицы.
 * Автоматически выбирает нужный компонент на основе `column.meta.dataType`.
 */
export function FormField({ column, mode }: Readonly<FormFieldProps>) {
  if (!column.accessorKey) {
    return null;
  }

  const dataType = column.meta?.dataType ?? ColumnDataTypes.TEXT;
  const FieldComponent = getFieldComponent(dataType);

  return (
    <FieldComponent
      column={column}
      mode={mode}
    />
  );
}

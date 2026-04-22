import { useFormContext } from 'react-hook-form';

import type { FormColumnDef } from '../../types';
import { isColumnRequired } from '../column-utils';

/**
 * Хук для получения общих пропсов и утилит от react-hook-form.
 * Использует FormContext от react-hook-form.
 *
 * @param column Колонка таблицы с мета-информацией.
 * @param mode Режим формы ('add' или 'edit').
 * @returns Объект с пропсами поля и утилитами формы.
 */
export function useFormField(column: FormColumnDef, mode: 'add' | 'edit') {
  const { control, watch, setValue, setError, clearErrors, trigger } = useFormContext();

  const columnId = String(column.accessorKey);
  const isIdField = columnId === 'id';

  return {
    columnId,
    label: typeof column.header === 'string' ? column.header : columnId || 'Поле',
    isReadOnly: (mode === 'edit' && (isIdField || column.meta?.readOnlyEdit)) || Boolean(column.meta?.readOnly),
    isRequired: isColumnRequired(column.meta),
    control,
    setValue,
    watch,
    trigger,
    setError,
    clearErrors,
    setFormError: (message: string) =>
      setError('root.submitError', {
        type: 'custom',
        message,
      }),
  };
}

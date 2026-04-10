import { Controller } from 'react-hook-form';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { getErrorMessage } from '@/shared/lib/error-message';
import { CreatableMultiSelect } from '@/shared/ui/CreatableSelect';

import type { SelectOption } from '../../../types';
import { isMultiSelectMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/**
 * Поле множественного выбора категорий.
 * Поддерживает CRUD операции (создание, редактирование, удаление) при наличии `meta.handlers`.
 */
export function MultiSelectField({ column, mode }: FormFieldProps) {
  const { columnId, label, isReadOnly, isRequired, control, watch, trigger, setFormError } = useFormField(column, mode);

  const meta = isMultiSelectMeta(column.meta) ? column.meta : null;
  const { options = EMPTY_ARRAY, handlers } = meta || {};

  const handleSelect = (selectedOptions: readonly SelectOption[], fieldOnChange: (value: unknown) => void) => {
    fieldOnChange(selectedOptions.map((o) => o.value));
  };

  const handleCreate = async (newLabel: string, fieldOnChange: (value: unknown) => void) => {
    if (!handlers?.onCreate) return;

    const currentValues = (watch(columnId) as string[]) ?? [];
    try {
      const newOption = await handlers.onCreate(newLabel);
      const selectedOptions = options.filter((item) => currentValues.includes(item.value));
      handleSelect([...selectedOptions, newOption], fieldOnChange);
    } catch (error) {
      fieldOnChange(currentValues);
      setFormError(getErrorMessage(error, 'Ошибка при создании'));
    }
  };

  const handleRename = async (value: string, newLabel: string) => {
    if (!handlers?.onEdit) return;

    try {
      await handlers.onEdit(value, newLabel);
    } catch (error) {
      setFormError(getErrorMessage(error, 'Ошибка при переименовании'));
    }
  };

  const handleDelete = async (option: SelectOption) => {
    if (!handlers?.onDelete) return false;

    try {
      return await handlers.onDelete(option.value);
    } catch (error) {
      setFormError(getErrorMessage(error, 'Ошибка при удалении'));
      return false;
    }
  };

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => (
        <CreatableMultiSelect
          options={options}
          value={field.value as string[] | undefined}
          onChange={(opts) => handleSelect(opts, field.onChange)}
          onCreate={handlers?.onCreate && ((label) => handleCreate(label, field.onChange))}
          onRename={handlers?.onEdit && handleRename}
          onDelete={handlers?.onDelete && handleDelete}
          onBlur={() => trigger(columnId)}
          onClear={() => field.onChange(EMPTY_ARRAY)}
          label={label}
          withAsterisk={isRequired}
          readOnly={isReadOnly}
          disabled={isReadOnly}
          error={fieldState.error?.message}
        />
      )}
    />
  );
}

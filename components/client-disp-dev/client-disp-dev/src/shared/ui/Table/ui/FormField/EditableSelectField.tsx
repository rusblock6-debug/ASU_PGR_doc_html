import { Controller, type ControllerRenderProps, type FieldValues } from 'react-hook-form';

import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { getErrorMessage } from '@/shared/lib/error-message';
import { hasValue } from '@/shared/lib/has-value';
import { CreatableSelect } from '@/shared/ui/CreatableSelect';
import type { SelectOption } from '@/shared/ui/types';

import { isEditableSelectMeta } from '../../lib/column-utils';
import { formatSelectValue } from '../../lib/formatters';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

type FieldOnChange = ControllerRenderProps<FieldValues, string>['onChange'];

/**
 * Поле c выпадающим списком с возможностью создавать, редактировать и удалять запись.
 * Поддерживает автозаполнение связанных полей и CRUD операции.
 */
export function EditableSelectField({ column, mode }: FormFieldProps) {
  const { columnId, label, isReadOnly, isRequired, control, setValue, trigger, setFormError } = useFormField(
    column,
    mode,
  );

  const meta = isEditableSelectMeta(column.meta) ? column.meta : null;
  const { autoFill, options = EMPTY_ARRAY, valueType = 'string', handlers } = meta || {};

  const autoFillFields = autoFill ? Object.keys(Object.values(autoFill)[0] ?? {}) : EMPTY_ARRAY;

  const fillRelatedFields = (fillData: Record<string, unknown> | null | undefined) => {
    // Если есть данные — заполняем, иначе сбрасываем все поля в null
    const dataToFill = fillData ?? Object.fromEntries(autoFillFields.map((key) => [key, null]));

    Object.entries(dataToFill).forEach(([fieldKey, fieldValue]) => {
      setValue(fieldKey, fieldValue ?? null, { shouldDirty: true, shouldValidate: true });
    });
  };

  const handleSelect = (option: SelectOption, fieldOnChange: FieldOnChange) => {
    const { value } = option;
    fieldOnChange(formatSelectValue(value, valueType));

    // Автозаполняем связанные поля
    if (autoFillFields.length > 0) {
      const fillData = hasValue(value) ? autoFill?.[value] : null;
      fillRelatedFields(fillData);
    }
  };

  const handleCreate = async (newLabel: string, fieldOnChange: FieldOnChange) => {
    if (!handlers?.onCreate) return;

    try {
      const newOption = await handlers.onCreate(newLabel);
      if (!hasValue(newOption)) return;

      fieldOnChange(formatSelectValue(newOption.value, valueType));

      // При создании сбрасываем связанные поля в null (пользователь заполнит вручную)
      fillRelatedFields(null);
    } catch (error) {
      // При ошибке оставляем поля пустыми для ручного заполнения
      fieldOnChange(null);
      setFormError(getErrorMessage(error));
    }
  };

  const handleRename = async (value: string, newLabel: string) => {
    if (!handlers?.onEdit) return;

    try {
      await handlers.onEdit(value, newLabel);
    } catch (error) {
      setFormError(getErrorMessage(error));
      throw error;
    }
  };

  const handleDelete = async (option: SelectOption, currentValue: unknown, fieldOnChange: FieldOnChange) => {
    if (!handlers?.onDelete) return false;

    try {
      const deleted = await handlers.onDelete(option.value);

      // Если удаление подтверждено и удаляем текущее значение — сбрасываем связанные поля
      if (deleted && String(currentValue) === option.value) {
        fieldOnChange(null);
        fillRelatedFields(null);
      }

      return deleted;
    } catch (error) {
      setFormError(getErrorMessage(error));
      throw error;
    }
  };

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => (
        <CreatableSelect
          options={options}
          value={hasValue(field.value) ? String(field.value) : null}
          onChange={(option) => handleSelect(option, field.onChange)}
          onCreate={handlers?.onCreate && ((newLabel) => handleCreate(newLabel, field.onChange))}
          onRename={handlers?.onEdit && handleRename}
          onDelete={handlers?.onDelete && ((option) => handleDelete(option, field.value, field.onChange))}
          onBlur={() => trigger(columnId)}
          onClear={() => field.onChange(null)}
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

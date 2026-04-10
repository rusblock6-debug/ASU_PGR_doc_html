import { Controller, type ControllerRenderProps, type FieldValues, useFormContext } from 'react-hook-form';

import { getErrorMessage } from '@/shared/lib/error-message';
import { hasValue } from '@/shared/lib/has-value';
import { CreatableSelect } from '@/shared/ui/CreatableSelect';
import type { SelectOption } from '@/shared/ui/types';

import type { FormFieldProps } from './types';

type FieldOnChange = ControllerRenderProps<FieldValues, string>['onChange'];

/**
 * Представляет свойства компонента поля c выпадающим списком с возможностью создавать, редактировать и удалять запись.
 */
interface EditableSelectField extends FormFieldProps {
  /** Возвращает список опций для выпадающего списка. */
  readonly options: readonly SelectOption[];
  /** Возвращает делегат, вызываемый при изменении значения. */
  readonly onChange: (value: string | null) => void;
  /** Возвращает обработчики изменений элементов списка. */
  readonly handlers: {
    /** Возвращает делегат, вызываемый при создании элемента списка. */
    readonly onCreate: (label: string) => Promise<SelectOption>;
    /** Возвращает делегат, вызываемый при изменении элемента списка. */
    readonly onEdit: (value: string, newLabel: string) => Promise<void>;
    /** Возвращает делегат, вызываемый при удалении элемента списка. */
    readonly onDelete: (value: string) => Promise<boolean>;
  };
}

/**
 * Поле c выпадающим списком с возможностью создавать, редактировать и удалять запись.
 * Поддерживает CRUD операции.
 */
export function EditableSelectField({
  name,
  label,
  required,
  readOnly,
  disabled,
  options,
  onChange,
  handlers,
}: EditableSelectField) {
  const { control, trigger, setError } = useFormContext();

  const setFormError = (message: string) =>
    setError('root.submitError', {
      type: 'custom',
      message,
    });

  const handleSelect = (option: SelectOption, fieldOnChange: FieldOnChange) => {
    const { value } = option;
    fieldOnChange(value);
    onChange(value);
  };

  const handleCreate = async (newLabel: string, fieldOnChange: FieldOnChange) => {
    try {
      const newOption = await handlers.onCreate(newLabel);
      if (!hasValue(newOption)) return;

      fieldOnChange(newOption.value);

      onChange(null);
    } catch (error) {
      fieldOnChange(null);
      setFormError(getErrorMessage(error));
    }
  };

  const handleRename = async (value: string, newLabel: string) => {
    try {
      await handlers.onEdit(value, newLabel);
    } catch (error) {
      setFormError(getErrorMessage(error));
      throw error;
    }
  };

  const handleDelete = async (option: SelectOption, currentValue: unknown, fieldOnChange: FieldOnChange) => {
    try {
      const deleted = await handlers.onDelete(option.value);

      if (deleted && String(currentValue) === option.value) {
        fieldOnChange(null);
        onChange(null);
      }

      return deleted;
    } catch (error) {
      setFormError(getErrorMessage(error));
      throw error;
    }
  };

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <CreatableSelect
          options={options}
          value={hasValue(field.value) ? String(field.value) : null}
          onChange={(option) => handleSelect(option, field.onChange)}
          onCreate={(newLabel) => handleCreate(newLabel, field.onChange)}
          onRename={handleRename}
          onDelete={(option) => handleDelete(option, field.value, field.onChange)}
          onBlur={() => trigger(name)}
          onClear={() => field.onChange(null)}
          label={label}
          withAsterisk={required}
          readOnly={readOnly}
          disabled={disabled}
          error={fieldState.error?.message}
        />
      )}
    />
  );
}

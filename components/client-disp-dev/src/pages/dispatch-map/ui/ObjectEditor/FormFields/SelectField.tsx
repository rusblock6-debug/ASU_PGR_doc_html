import { Controller, useFormContext } from 'react-hook-form';

import { Select } from '@/shared/ui/Select';
import type { SelectOption } from '@/shared/ui/types';

import type { FormFieldProps } from './types';

/**
 * Свойства компонента поля выбора из выпадающего списка.
 */
interface SelectFieldProps extends FormFieldProps {
  /** Если установлено, становится возможным отменить выбор значения, щелкнув по выбранной опции. */
  readonly allowDeselect?: boolean;
  /** Список опций. */
  readonly options: readonly SelectOption[];
  /** Колбэк при изменении значения пользователем. */
  readonly onChange?: (value: string | null) => void;
}

/**
 * Компонент поля выбора из выпадающего списка.
 */
export function SelectField({
  allowDeselect,
  name,
  label,
  required,
  readOnly,
  disabled,
  options,
  onChange,
}: SelectFieldProps) {
  const { control } = useFormContext();

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => (
        <Select
          {...field}
          allowDeselect={allowDeselect}
          onChange={(value) => {
            field.onChange(value);
            onChange?.(value);
          }}
          withAsterisk={required}
          data={options}
          label={label}
          error={fieldState.error?.message}
          readOnly={readOnly}
          disabled={disabled}
        />
      )}
    />
  );
}

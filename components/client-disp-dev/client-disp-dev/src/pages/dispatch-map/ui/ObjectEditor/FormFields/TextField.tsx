import { Controller, useFormContext } from 'react-hook-form';

import { TextInput } from '@/shared/ui/TextInput';

import type { FormFieldProps } from './types';

/**
 * Компонент поля ввода текса.
 */
export function TextField({ name, label, required, readOnly, disabled }: Readonly<FormFieldProps>) {
  const { control } = useFormContext();

  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <TextInput
          {...field}
          withAsterisk={required}
          placeholder="Не указан"
          label={label}
          error={fieldState.error?.message}
          readOnly={readOnly}
          disabled={disabled}
        />
      )}
    />
  );
}

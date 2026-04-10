import { Controller, useFormContext } from 'react-hook-form';

import { NumberInput } from '@/shared/ui/NumberInput';

import type { FormFieldProps } from './types';

/**
 * Компонент поля ввода числа.
 */
export function NumberField({ name, label, required, readOnly, disabled }: Readonly<FormFieldProps>) {
  const { control } = useFormContext();

  return (
    <Controller
      control={control}
      name={name}
      render={({ field, fieldState }) => (
        <NumberInput
          {...field}
          withAsterisk={required}
          value={(field.value as string | number | undefined) ?? ''}
          label={label}
          error={fieldState.error?.message}
          readOnly={readOnly}
          disabled={disabled}
          hideControls
        />
      )}
    />
  );
}

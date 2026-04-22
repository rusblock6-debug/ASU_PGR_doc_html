import { Controller } from 'react-hook-form';

import { NumberInput } from '@/shared/ui/NumberInput';

import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Числовое поле формы. */
export function NumberField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => (
        <NumberInput
          {...field}
          withAsterisk={isRequired}
          value={(field.value as string | number) ?? ''}
          label={label}
          error={fieldState.error?.message}
          readOnly={isReadOnly}
          disabled={isReadOnly}
          hideControls
        />
      )}
    />
  );
}

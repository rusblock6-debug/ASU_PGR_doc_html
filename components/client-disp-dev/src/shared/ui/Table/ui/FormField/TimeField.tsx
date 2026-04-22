import { Controller } from 'react-hook-form';

import { TimeInput } from '@/shared/ui/TimeInput';

import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Поле ввода времени. */
export function TimeField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => (
        <TimeInput
          {...field}
          withAsterisk={isRequired}
          value={field.value !== null ? String(field.value) : '00:00'}
          onChange={(event) => {
            const value = event.currentTarget.value || '00:00';
            field.onChange(value);
          }}
          label={label}
          error={fieldState.error?.message}
          readOnly={isReadOnly}
          disabled={isReadOnly}
        />
      )}
    />
  );
}

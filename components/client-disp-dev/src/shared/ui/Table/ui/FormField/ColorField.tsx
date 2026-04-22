import { Controller } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { ColorInput } from '@/shared/ui/ColorInput';

import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Поле выбора цвета. */
export function ColorField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field: { value, onChange, onBlur }, fieldState }) => (
        <ColorInput
          onBlur={onBlur}
          withAsterisk={isRequired}
          value={hasValue(value) ? String(value) : undefined}
          onChange={onChange}
          label={label}
          error={fieldState.error?.message}
          readOnly={isReadOnly}
          disabled={isReadOnly}
        />
      )}
    />
  );
}

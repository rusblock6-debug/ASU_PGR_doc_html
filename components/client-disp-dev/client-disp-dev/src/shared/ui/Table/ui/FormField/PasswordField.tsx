import { Controller } from 'react-hook-form';

import { PasswordInput } from '@/shared/ui/PasswordInput';

import { isTextMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Поле формы для ввода пароля. */
export function PasswordField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  const meta = isTextMeta(column.meta) ? column.meta : null;
  const inputType = meta?.inputType;

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => {
        return (
          <PasswordInput
            {...field}
            type={inputType}
            withAsterisk={isRequired}
            label={label}
            error={fieldState.error?.message}
            readOnly={isReadOnly}
            disabled={isReadOnly}
          />
        );
      }}
    />
  );
}

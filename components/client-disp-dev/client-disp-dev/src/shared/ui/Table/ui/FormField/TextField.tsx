import { Controller } from 'react-hook-form';

import { formatMacAddress, MAC_ADDRESS_PLACEHOLDER } from '@/shared/lib/format-mac-address';
import { hasValue } from '@/shared/lib/has-value';
import { TextInput } from '@/shared/ui/TextInput';

import { isTextMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Текстовое поле формы. */
export function TextField({ column, mode }: FormFieldProps) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  const meta = isTextMeta(column.meta) ? column.meta : null;
  const isMacMask = meta?.mask === 'mac-address';

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => {
        const rawValue = hasValue(field.value) ? String(field.value) : '';
        const displayValue = isMacMask ? formatMacAddress(rawValue) : rawValue;

        return (
          <TextInput
            {...field}
            withAsterisk={isRequired}
            value={displayValue}
            onChange={(e) => {
              const value = isMacMask ? formatMacAddress(e.target.value) : e.target.value;
              field.onChange(value);
            }}
            placeholder={isMacMask ? MAC_ADDRESS_PLACEHOLDER : 'Не указан'}
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

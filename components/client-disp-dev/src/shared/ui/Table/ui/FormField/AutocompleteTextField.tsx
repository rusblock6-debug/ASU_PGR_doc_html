import { Controller } from 'react-hook-form';

import { Autocomplete } from '@/shared/ui/Autocomplete';

import { isAutocompleteTextMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Текстовое поле с предлагаемыми вариантами заполнения формы. */
export function AutocompleteTextField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control } = useFormField(column, mode);

  const meta = isAutocompleteTextMeta(column.meta) ? column.meta : null;
  const options = meta?.options;

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field, fieldState }) => {
        return (
          <Autocomplete
            {...field}
            data={options}
            withAsterisk={isRequired}
            placeholder="Не указан"
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

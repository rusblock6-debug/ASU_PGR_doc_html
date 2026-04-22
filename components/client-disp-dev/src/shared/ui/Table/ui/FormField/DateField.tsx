'use no memo';

import { Controller } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { DateInput } from '@/shared/ui/DateInput';

import { isDateMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Поле выбора даты. */
export function DateField({ column, mode }: Readonly<FormFieldProps>) {
  const { columnId, label, isReadOnly, isRequired, control, watch } = useFormField(column, mode);
  const tz = useTimezone();
  const formWatch = watch();

  const meta = isDateMeta(column.meta) ? column.meta : null;
  const columnWithMinValue = meta?.columnWithMinValue;
  const columnWithMaxValue = meta?.columnWithMaxValue;

  return (
    <Controller
      name={columnId}
      control={control}
      render={({ field: { value, onChange, onBlur }, fieldState }) => (
        <DateInput
          withAsterisk={isRequired}
          onBlur={onBlur}
          value={hasValue(value) ? new Date(value as string) : null}
          onChange={(date) => onChange(hasValue(date) ? tz.format(date, 'yyyy-MM-dd') : null)}
          label={label}
          error={fieldState.error?.message}
          readOnly={isReadOnly}
          disabled={isReadOnly}
          minDate={
            hasValue(columnWithMinValue) && formWatch[columnWithMinValue]
              ? new Date(formWatch[columnWithMinValue] as string)
              : undefined
          }
          maxDate={
            hasValue(columnWithMaxValue) && formWatch[columnWithMaxValue]
              ? new Date(formWatch[columnWithMaxValue] as string)
              : undefined
          }
        />
      )}
    />
  );
}

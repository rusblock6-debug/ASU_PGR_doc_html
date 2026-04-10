'use no memo';

import { Controller } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { DateTimePicker } from '@/shared/ui/DateTimePicker';

import { isDateMeta } from '../../lib/column-utils';
import { useFormField } from '../../lib/hooks/useFormField';
import type { FormFieldProps } from '../../types';

/** Поле выбора даты и времени. */
export function DateTimeField({ column, mode }: FormFieldProps) {
  const { columnId, label, isReadOnly, isRequired, control, watch, trigger } = useFormField(column, mode);
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
        <DateTimePicker
          onBlur={onBlur}
          value={hasValue(value) ? tz.toTimezone(new Date(value as string)) : null}
          onChange={(date) => {
            onChange(date ? tz.toUTC(new Date(date)) : null);
            void trigger();
          }}
          label={label}
          error={fieldState.error?.message}
          withAsterisk={isRequired}
          readOnly={isReadOnly}
          disabled={isReadOnly}
          minDate={
            hasValue(columnWithMinValue) && formWatch[columnWithMinValue]
              ? tz.toTimezone(new Date(formWatch[columnWithMinValue]))
              : undefined
          }
          maxDate={
            hasValue(columnWithMaxValue) && formWatch[columnWithMaxValue]
              ? tz.toTimezone(new Date(formWatch[columnWithMaxValue]))
              : undefined
          }
        />
      )}
    />
  );
}

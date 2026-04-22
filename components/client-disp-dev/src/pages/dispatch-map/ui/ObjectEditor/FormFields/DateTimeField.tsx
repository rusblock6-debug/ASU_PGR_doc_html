import { Controller, useFormContext } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { DateTimePicker } from '@/shared/ui/DateTimePicker';

import type { FormFieldProps } from './types';

/**
 * Свойства компонента поля ввода даты и времени.
 */
interface DateTimeFieldProps extends FormFieldProps {
  /** Минимальное значение. */
  readonly minDate?: string | null;
  /** Максимальное значение. */
  readonly maxDate?: string | null;
}

/** Поле выбора даты и времени. */
export function DateTimeField({ name, label, required, readOnly, disabled, minDate, maxDate }: DateTimeFieldProps) {
  const { control } = useFormContext();
  const tz = useTimezone();

  return (
    <Controller
      name={name}
      control={control}
      render={({ field: { value, onChange, onBlur }, fieldState }) => (
        <DateTimePicker
          withAsterisk={required}
          onBlur={onBlur}
          value={hasValue(value) ? tz.toTimezone(new Date(value as string)) : null}
          onChange={(date) => {
            onChange(hasValue(date) ? tz.format(date, 'yyyy-MM-dd') : null);
          }}
          label={label}
          error={fieldState.error?.message}
          readOnly={readOnly}
          disabled={disabled}
          minDate={hasValue(minDate) ? minDate : undefined}
          maxDate={hasValue(maxDate) ? maxDate : undefined}
        />
      )}
    />
  );
}

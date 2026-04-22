import { Controller, useFormContext } from 'react-hook-form';

import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { DateInput } from '@/shared/ui/DateInput';

import type { FormFieldProps } from './types';

/**
 * Свойства компонента поля ввода даты.
 */
interface DateFieldProps extends FormFieldProps {
  /** Минимальное значение. */
  readonly minDate?: string | null;
  /** Максимальное значение. */
  readonly maxDate?: string | null;
}

/**
 * Компонент поля ввода даты.
 */
export function DateField({ name, label, required, readOnly, disabled, minDate, maxDate }: DateFieldProps) {
  const { control } = useFormContext();
  const tz = useTimezone();

  return (
    <Controller
      name={name}
      control={control}
      render={({ field: { value, onChange, onBlur }, fieldState }) => (
        <DateInput
          withAsterisk={required}
          onBlur={onBlur}
          value={hasValue(value) ? new Date(value as string) : null}
          onChange={(date) => onChange(hasValue(date) ? tz.format(date, 'yyyy-MM-dd') : null)}
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

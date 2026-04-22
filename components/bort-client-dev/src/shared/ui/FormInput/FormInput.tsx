import type { FocusEventHandler, Ref } from 'react';
import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './FormInput.module.css';

/**
 * Текстовое поле, связанное с react-hook-form через `Controller` (ref для kiosk-фокуса).
 */
export function FormInput<T extends FieldValues>({
  control,
  name,
  placeholder,
  type = 'text',
  autoComplete,
  id,
  className,
  hasError,
  selected,
  onFocus,
  inputRef,
}: {
  readonly control: Control<T>;
  readonly name: Path<T>;
  readonly placeholder?: string;
  readonly type?: HTMLInputElement['type'];
  readonly autoComplete?: string;
  readonly id?: string;
  readonly className?: string;
  /** Подсветка ошибки валидации (граница). */
  readonly hasError?: boolean;
  /** Подсветка выбранного поля в kiosk-навигации. */
  readonly selected?: boolean;
  readonly onFocus?: FocusEventHandler<HTMLInputElement>;
  readonly inputRef?: Ref<HTMLInputElement>;
}) {
  return (
    <Controller
      control={control}
      name={name}
      render={({ field }) => (
        <input
          autoComplete={autoComplete}
          className={cn(
            styles.input,
            hasError && styles.input_error,
            selected && !hasError && styles.input_selected,
            className,
          )}
          id={id}
          name={field.name}
          onBlur={field.onBlur}
          onChange={field.onChange}
          onFocus={(event) => {
            onFocus?.(event);
          }}
          placeholder={placeholder}
          ref={(element) => {
            field.ref(element);
            if (typeof inputRef === 'function') {
              inputRef(element);
            } else if (inputRef) {
              inputRef.current = element;
            }
          }}
          type={type}
          value={field.value ?? ''}
        />
      )}
    />
  );
}

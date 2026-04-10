import { TimeInput as MantineTimeInput, type TimeInputProps as MantineTimeInputProps } from '@mantine/dates';
import { forwardRef } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import type { BaseInputOption } from '@/shared/ui/types';

/**
 * Представляет свойства для компонента ввода времени.
 * https://mantine.dev/dates/time-input/
 */
export interface TimeInputProps extends Omit<MantineTimeInputProps, 'variant' | 'inputSize'>, BaseInputOption {}

/**
 * Адаптер компонента TimeInput из Mantine с предустановленными значениями по умолчанию.
 * Используется для ввода времени.
 */
export const TimeInput = forwardRef<HTMLInputElement, TimeInputProps>(
  (
    {
      inputSize = 'xs',
      variant = 'default',
      placeholder = 'Не указан',
      labelPosition = 'horizontal',
      className,
      classNames,
      ...props
    },
    ref,
  ) => {
    const classNamesObj = typeof classNames === 'object' ? classNames : undefined;

    return (
      <MantineTimeInput
        ref={ref}
        {...props}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        className={cn(className)}
        classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, classNamesObj)}
        variant={variant}
        placeholder={placeholder}
      />
    );
  },
);

TimeInput.displayName = 'TimeInput';

import { Textarea as MantineTextarea, type TextareaProps as MantineTextareaProps } from '@mantine/core';
import { forwardRef } from 'react';

import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import type { BaseInputOption } from '@/shared/ui/types';

/**
 * Представляет свойства для компонента многострочного текстового ввода.
 * https://mantine.dev/core/textarea/
 */
export interface TextareaProps extends Omit<MantineTextareaProps, 'variant' | 'inputSize'>, BaseInputOption {}

/**
 * Адаптер компонента Textarea из Mantine с предустановленными значениями по умолчанию.
 * Используется для многострочного текстового ввода с единообразным стилем по всему приложению.
 */
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      inputSize = 'xs',
      variant = 'default',
      labelPosition = 'horizontal',
      placeholder = 'Не указан',
      className,
      classNames,
      ...props
    },
    ref,
  ) => {
    const classNamesObj = typeof classNames === 'object' ? classNames : null;

    return (
      <MantineTextarea
        ref={ref}
        {...props}
        className={className}
        classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, classNamesObj)}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        variant={variant}
        placeholder={placeholder}
      />
    );
  },
);

Textarea.displayName = 'Textarea';

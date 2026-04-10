import {
  PasswordInput as MantinePasswordInput,
  type PasswordInputProps as MantinePasswordInputProps,
} from '@mantine/core';
import { useState } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './PasswordInput.module.css';

/**
 * Представляет свойства для компонента поля ввода пароля.
 * https://mantine.dev/core/password-input/
 */
export interface PasswordInputProps extends Omit<MantinePasswordInputProps, 'variant' | 'inputSize'>, BaseInputOption {}

/**
 * Адаптер компонента PasswordInput из Mantine.
 * Используется для ввода пароля с единообразным стилем по всему приложению.
 */
export function PasswordInput({
  inputSize = 'xs',
  variant = 'default',
  labelPosition = 'horizontal',
  placeholder = 'Не указан',
  className,
  classNames,
  ...props
}: PasswordInputProps) {
  const [passwordVisible, setPasswordVisible] = useState(false);

  const classNamesObj = typeof classNames === 'object' ? classNames : null;

  const isEmptyStringValue = typeof props.value === 'string' && !hasValueNotEmpty(props.value.trim());

  const { ref, isTextOverflowed } = useCheckTextOverflow(props.value);

  return (
    <Tooltip
      label={props.value}
      disabled={!isTextOverflowed || isEmptyStringValue || !passwordVisible}
    >
      <MantinePasswordInput
        ref={ref}
        {...props}
        className={className}
        classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, {
          ...classNamesObj,
          input: cn(styles.input, classNamesObj?.input),
        })}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        variant={variant}
        placeholder={placeholder}
        onVisibilityChange={setPasswordVisible}
      />
    </Tooltip>
  );
}

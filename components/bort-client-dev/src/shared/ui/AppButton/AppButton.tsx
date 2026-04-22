import type { ButtonProps as MantineButtonProps } from '@mantine/core';
import { Button } from '@mantine/core';
import React from 'react';

import { assertNever } from '@/shared/lib/assert-never';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './AppButton.module.css';

/**
 * Представляет варианты кнопки.
 */
type ButtonVariant = 'primary' | 'secondary' | 'clear';

/**
 * Представляет размеры кнопки.
 */
type ButtonSize = 'xl' | 'l' | 'm' | 's' | 'xs';

/**
 * Представляет свойства для компонента кнопки.
 */
interface AppButtonProps extends Omit<MantineButtonProps, 'variant' | 'size' | 'onlyIcon'> {
  /**
   * Возвращает вариант.
   */
  readonly variant?: ButtonVariant;
  /**
   * Возвращает размер.
   */
  readonly size?: ButtonSize;
  /**
   * Кнопка содержит только иконку без текста.
   */
  readonly onlyIcon?: boolean;
}

/**
 * Представляет компонент кнопки.
 */
export function AppButton({
  className,
  classNames,
  onlyIcon,
  style,
  size = 'm',
  variant = 'primary',
  ...restProps
}: AppButtonProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const classNamesObj = typeof classNames === 'object' ? classNames : undefined;

  return (
    <Button
      className={cn(
        styles.button,
        getClassNameByVariant(variant),
        getClassNameBySize(size),
        { [styles.button_only_icon]: onlyIcon },
        className,
      )}
      classNames={{
        label: cn(styles.label, classNamesObj?.label),
        ...classNamesObj,
      }}
      style={style}
      {...restProps}
      variant="unstyled"
    />
  );
}

/** Маппит variant AppButton на CSS-класс. */
function getClassNameByVariant(variant: ButtonVariant = 'primary') {
  switch (variant) {
    case 'primary':
      return '';
    case 'secondary':
      return styles.secondary ?? '';
    case 'clear':
      return styles.clear ?? '';
    default:
      return assertNever(variant);
  }
}

/** Маппит размер AppButton на CSS-класс. */
function getClassNameBySize(size: ButtonSize = 'm') {
  switch (size) {
    case 'xl':
      return styles.size_extra_large ?? '';
    case 'l':
      return styles.size_large ?? '';
    case 'm':
      return styles.size_medium ?? '';
    case 's':
      return styles.size_small ?? '';
    case 'xs':
      return styles.size_extra_small ?? '';
    default:
      return assertNever(size);
  }
}

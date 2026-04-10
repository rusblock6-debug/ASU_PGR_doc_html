import { TextInput as MantineTextInput, type TextInputProps as MantineTextInputProps } from '@mantine/core';
import React, { forwardRef } from 'react';

import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import CrossIcon from '@/shared/assets/icons/ic-cross.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './TextInput.module.css';

/**
 * Представляет свойства для компонента текстового ввода.
 * https://mantine.dev/core/text-input/
 */
export interface TextInputProps extends Omit<MantineTextInputProps, 'variant' | 'inputSize'>, BaseInputOption {
  /**
   * Показывать ли кнопку очистки.
   */
  readonly clearable?: boolean;
  /**
   * Показывать ли стрелку (для select-подобных компонентов).
   */
  readonly withArrow?: boolean;
  /**
   * Повернута ли стрелка (для состояния открыт или закрыт дропдаун).
   */
  readonly arrowRotated?: boolean;
  /**
   * Callback при нажатии на кнопку очистки.
   */
  readonly onClear?: () => void;
}

/**
 * Адаптер компонента TextInput из Mantine с предустановленными значениями по умолчанию.
 * Используется для текстового ввода с единообразным стилем по всему приложению.
 */
export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  (
    {
      inputSize = 'xs',
      variant = 'default',
      labelPosition = 'horizontal',
      placeholder = 'Не указан',
      className,
      classNames,
      clearable,
      withArrow,
      arrowRotated,
      rightSection,
      rightSectionWidth,
      onClear,
      ...props
    },
    ref,
  ) => {
    const classNamesObj = typeof classNames === 'object' ? classNames : null;

    const handleClear = (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onClear?.();
    };

    const clearButton = clearable ? (
      <button
        type="button"
        className={styles.clear_button}
        onClick={handleClear}
        onMouseDown={(e) => e.preventDefault()}
      >
        <CrossIcon
          width={16}
          height={16}
        />
      </button>
    ) : null;

    const arrowIcon = withArrow ? (
      <div className={styles.arrow_icon}>
        <ArrowDownIcon className={cn(styles.arrow, { [styles.arrow_rotated]: arrowRotated })} />
      </div>
    ) : null;

    // Определяем rightSection: приоритет у переданного, затем clearable, затем arrow
    const computedRightSection = rightSection ?? clearButton ?? arrowIcon;
    const hasRightSection = Boolean(clearable || withArrow || rightSection);

    const isEmptyStringValue = typeof props.value === 'string' && !hasValueNotEmpty(props.value.trim());

    const { ref: mergedRef, isTextOverflowed } = useCheckTextOverflow(props.value, ref);

    return (
      <Tooltip
        label={props.value}
        disabled={!isTextOverflowed || isEmptyStringValue}
      >
        <MantineTextInput
          ref={mergedRef}
          {...props}
          className={cn({ [styles.clearable]: clearable }, { [styles.with_arrow]: withArrow }, className)}
          classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, classNamesObj)}
          mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
          rightSection={computedRightSection}
          rightSectionWidth={rightSectionWidth ?? (hasRightSection ? 32 : undefined)}
          rightSectionPointerEvents={withArrow && !clearable && !rightSection ? 'none' : undefined}
          variant={variant}
          placeholder={placeholder}
        />
      </Tooltip>
    );
  },
);

TextInput.displayName = 'TextInput';

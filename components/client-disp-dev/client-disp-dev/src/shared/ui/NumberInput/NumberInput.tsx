import { NumberInput as MantineNumberInput, type NumberInputProps as MantineNumberInputProps } from '@mantine/core';

import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { BaseInputOption } from '@/shared/ui/types';

/**
 * Представляет свойства для компонента числового ввода.
 * https://mantine.dev/core/number-input/
 */
export interface NumberInputProps
  extends Omit<MantineNumberInputProps, 'hideControls' | 'variant' | 'inputSize'>, BaseInputOption {
  /**
   * Показывать ли элементы управления (кнопки увеличения/уменьшения).
   *
   * @default false
   */
  readonly hideControls?: boolean;
}

/**
 * Адаптер компонента NumberInput из Mantine с предустановленными значениями по умолчанию.
 * Используется для числового ввода с единообразным стилем по всему приложению.
 */
export function NumberInput({
  hideControls = true,
  inputSize = 'xs',
  variant = 'default',
  placeholder = 'Не указан',
  labelPosition = 'horizontal',
  classNames,
  ...props
}: NumberInputProps) {
  const classNamesObj = typeof classNames === 'object' ? classNames : null;

  const { ref, isTextOverflowed } = useCheckTextOverflow(props.value);

  return (
    <Tooltip
      label={props.value}
      disabled={!isTextOverflowed || !hasValueNotEmpty(props.value)}
    >
      <MantineNumberInput
        {...props}
        ref={ref}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, classNamesObj)}
        hideControls={hideControls}
        variant={variant}
        placeholder={placeholder}
      />
    </Tooltip>
  );
}

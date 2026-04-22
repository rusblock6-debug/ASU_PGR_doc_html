import { ColorInput as MantineColorInput, type ColorInputProps as MantineColorInputProps } from '@mantine/core';

import { cn } from '@/shared/lib/classnames-utils';
import { Z_INDEX } from '@/shared/lib/constants';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './ColorInput.module.css';

/**
 * Представляет свойства для компонента.
 * https://mantine.dev/core/color-input/
 */
export interface ColorPickerProps extends Omit<MantineColorInputProps, 'variant' | 'inputSize'>, BaseInputOption {
  /**
   * Возвращает значение zIndex.
   */
  readonly zIndex?: number;
}

/**
 * Представляет компонент поля ввода цвета.
 */
export function ColorInput(props: ColorPickerProps) {
  const {
    zIndex = Z_INDEX.MODAL,
    format = 'hex',
    popoverProps,
    classNames,
    inputSize = 'xs',
    variant = 'default',
    placeholder = 'Не указан',
    labelPosition = 'horizontal',
    ...defaultProps
  } = props;

  const classNamesObj = typeof classNames === 'object' ? classNames : undefined;

  return (
    <MantineColorInput
      {...defaultProps}
      mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
      format={format}
      variant={variant}
      placeholder={placeholder}
      popoverProps={{
        ...popoverProps,
        zIndex,
      }}
      classNames={mergeMantineClassNames(mantineInput, mantineInputWrapper, {
        ...classNamesObj,
        input: cn(styles.input, classNamesObj?.input),
      })}
    />
  );
}

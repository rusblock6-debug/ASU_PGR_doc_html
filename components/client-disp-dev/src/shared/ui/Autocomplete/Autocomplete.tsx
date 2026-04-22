import { Autocomplete as MantineAutocomplete, type AutocompleteProps as MantineAutocompleteProps } from '@mantine/core';

import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './Autocomplete.module.css';

/**
 * Представляет свойства текстового поля ввода со списком предлагаемых значений.
 */
interface AutocompleteProps
  extends Omit<MantineAutocompleteProps, 'classNames' | 'inputSize' | 'variant'>, BaseInputOption {
  /** Классы для кастомизации внутренних элементов. */
  readonly classNames?: Record<string, string | undefined>;
}

/**
 * Представляет компонент текстового поля ввода со списком предлагаемых значений.
 */
export function Autocomplete(props: AutocompleteProps) {
  const {
    classNames,
    inputSize = 'xs',
    variant = 'default',
    placeholder = 'Не указан',
    labelPosition = 'horizontal',
    ...restProps
  } = props;
  const { ref, isTextOverflowed } = useCheckTextOverflow(props.value);

  return (
    <Tooltip
      label={props.value}
      disabled={!isTextOverflowed}
    >
      <MantineAutocomplete
        {...restProps}
        ref={ref}
        inputSize={inputSize}
        variant={variant}
        placeholder={placeholder}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        classNames={mergeMantineClassNames(classNames, mantineInput, mantineInputWrapper, {
          option: styles.option,
          dropdown: styles.dropdown,
        })}
        comboboxProps={{
          withinPortal: false,
          offset: 2,
          ...restProps.comboboxProps,
        }}
      />
    </Tooltip>
  );
}

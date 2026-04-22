import { Select as MantineSelect, type SelectProps as MantineSelectProps } from '@mantine/core';
import { useMemo } from 'react';

import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { mergeMantineClassNames } from '@/shared/lib/merge-mantine-classnames';
import { mantineInput, mantineInputWrapper } from '@/shared/styles/mantine';
import { Tooltip } from '@/shared/ui/Tooltip';
import type { BaseInputOption } from '@/shared/ui/types';

import styles from './Select.module.css';

/**
 * Представляет свойства компонента Select.
 */
export type SelectProps<T extends string> = BaseInputOption &
  Omit<MantineSelectProps, 'data' | 'onChange' | 'classNames' | 'mod'> & {
    /** Разместить выбранный элемент первым в списке опций. */
    readonly isSelectedFirst?: boolean;
    /** Список опций: value — значение, label — подпись. */
    readonly data: readonly { readonly value: T; readonly label: string }[];
    /** Вызывается при смене выбора; аргумент — выбранное value или null при сбросе. */
    readonly onChange?: (value: T | null) => void;
    /** Классы для кастомизации внутренних элементов. */
    readonly classNames?: Record<string, string | undefined>;
    /** Состояние предупреждения. */
    readonly warning?: boolean;
  };

/**
 * Компонент для выбора опции.
 */
export function Select<T extends string>({
  inputSize = 'xs',
  variant = 'default',
  placeholder = 'Не указан',
  labelPosition = 'horizontal',
  isSelectedFirst = false,
  data,
  onChange,
  classNames = {},
  value,
  clearable = false,
  warning = false,
  ...mantineProps
}: SelectProps<T>) {
  const { readOnly, comboboxProps } = mantineProps;

  const sortedData = useMemo(() => {
    if (!hasValue(value) || !isSelectedFirst) return data;

    const selectedItem = data.find((item) => item.value === value);
    const otherItems = data.filter((item) => item.value !== value);

    return selectedItem ? [selectedItem, ...otherItems] : data;
  }, [data, isSelectedFirst, value]);

  const getRightSection = () => {
    if (readOnly) {
      return <div />;
    }
    if (!clearable || !value) {
      return <ArrowDownIcon className={styles.icon} />;
    }
    return undefined;
  };

  const handleChange = (value: string | null) => {
    onChange?.(value as T | null);
  };

  const tooltipLabel = useMemo(() => sortedData.find((item) => item.value === value)?.label, [sortedData, value]);

  const { ref, isTextOverflowed } = useCheckTextOverflow(tooltipLabel);

  return (
    <Tooltip
      label={tooltipLabel}
      disabled={!isTextOverflowed || !hasValueNotEmpty(tooltipLabel)}
    >
      <MantineSelect
        {...mantineProps}
        ref={ref}
        mod={{ 'input-size': inputSize, 'label-position': labelPosition }}
        variant={variant}
        placeholder={placeholder}
        data={sortedData}
        value={value}
        onChange={handleChange}
        clearable={clearable}
        nothingFoundMessage="Ничего не найдено"
        classNames={mergeMantineClassNames(classNames, mantineInput, mantineInputWrapper, {
          input: cn(styles.input, { [styles.input_warning]: warning }, { [styles.read_only]: readOnly }),
          error: styles.error,
          option: styles.option,
          dropdown: cn(styles.dropdown, getDropdownClassNameByVariant(variant)),
        })}
        rightSection={getRightSection()}
        rightSectionPointerEvents="none"
        comboboxProps={{
          withinPortal: false,
          offset: 2,
          ...comboboxProps,
        }}
      />
    </Tooltip>
  );
}

/** Возвращает имя класса для стилизации выпадающего списка. */
function getDropdownClassNameByVariant(variant: SelectProps<string>['variant'] = 'default') {
  switch (variant) {
    case 'default':
      return styles.default;
    case 'combobox-primary':
      return styles.combobox_primary;
    default:
      return undefined;
  }
}

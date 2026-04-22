import { SegmentedControl, type SegmentedControlProps } from '@mantine/core';

import styles from './ToggleSwitch.module.css';

/**
 * Представляет свойства для компонента переключателя.
 */
interface ToggleSwitchProps<T extends string> extends Omit<SegmentedControlProps, 'onChange' | 'data'> {
  /**
   * Возвращает источник данных.
   */
  readonly data: { label: string; value: T }[];
  /**
   * Возвращает делегат, вызываемый при изменении активного элемента.
   */
  readonly onChange?: (value: T) => void;
}

/**
 * Представляет компонент переключателя (радиокнопки).
 */
export function ToggleSwitch<T extends string>({ data, onChange, ...props }: ToggleSwitchProps<T>) {
  const handleChange = (value: string) => {
    const selectedItem = data.find((item) => item.value === value);
    if (selectedItem) {
      onChange?.(selectedItem.value);
    }
  };

  return (
    <SegmentedControl
      {...props}
      className={styles.general}
      classNames={{
        root: styles.root,
        control: styles.control,
        label: styles.label,
        indicator: styles.indicator,
        innerLabel: styles.inner_label,
      }}
      data={data}
      onChange={handleChange}
    />
  );
}

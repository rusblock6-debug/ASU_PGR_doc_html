import { Pill } from '@mantine/core';

import type { SelectOption } from '@/shared/ui/types';

import styles from './PillItem.module.css';

/** Свойства компонента для отображения выбранной опции в виде пилюли с возможностью удаления. */
interface PillItemProps<T extends SelectOption> {
  /** Опция для отображения. */
  readonly option: T;
  /** Заблокировано для взаимодействия. */
  readonly disabled?: boolean;
  /** Только для чтения. */
  readonly readOnly?: boolean;
  /** Callback при удалении опции. */
  readonly onRemove: (value: string) => void;
}

/** Компонент для отображения выбранной опции в виде пилюли с возможностью удаления. */
export function PillItem<T extends SelectOption>({ option, onRemove, disabled, readOnly }: PillItemProps<T>) {
  const handleRemove = () => {
    if (!disabled && !readOnly) {
      onRemove(option.value);
    }
  };

  return (
    <Pill
      unstyled
      classNames={{
        root: styles.pill_root,
        label: styles.pill_label_inner,
        remove: styles.pill_remove,
      }}
      withRemoveButton={!disabled && !readOnly}
      onRemove={handleRemove}
      title={option.label}
      data-pill-item="true"
    >
      {option.label}
    </Pill>
  );
}

import { UnstyledButton } from '@mantine/core';
import { useState } from 'react';

import { cn } from '@/shared/lib/classnames-utils';

import { FloatingIndicator } from './FloatingIndicator';
import styles from './FloatingIndicatorGroup.module.css';

/** Элемент данных для FloatingIndicatorGroup. */
export interface FloatingIndicatorGroupItem<T extends string> {
  /** Значение элемента. */
  readonly value: T;
  /** Отображаемый текст. */
  readonly label: string;
  /** Если `true`, элемент недоступен для выбора. */
  readonly disabled?: boolean;
}

/** Представляет свойства компонента FloatingIndicatorGroup. */
interface FloatingIndicatorGroupProps<T extends string> {
  /** Массив элементов для отображения. */
  readonly data: readonly FloatingIndicatorGroupItem<T>[];
  /** Текущее активное значение. */
  readonly value: T;
  /** Колбэк при смене значения. */
  readonly onChange: (value: T) => void;
  /** CSS-классы для кастомизации отдельных частей компонента. */
  readonly classNames?: Partial<Record<'root' | 'control' | 'label' | 'indicator', string>>;
}

/**
 * Переключатель с плавающим индикатором.
 */
export function FloatingIndicatorGroup<T extends string>({
  data,
  value,
  onChange,
  classNames,
}: FloatingIndicatorGroupProps<T>) {
  const [rootRef, setRootRef] = useState<HTMLDivElement | null>(null);
  const [controlsRefs, setControlsRefs] = useState<Record<string, HTMLButtonElement | null>>({});

  const setControlRef = (itemValue: T) => (node: HTMLButtonElement) => {
    setControlsRefs((prev) => ({ ...prev, [itemValue]: node }));
  };

  return (
    <div
      className={cn(styles.root, classNames?.root)}
      ref={setRootRef}
    >
      {data.map((item) => (
        <UnstyledButton
          key={item.value}
          className={cn(styles.control, classNames?.control)}
          ref={setControlRef(item.value)}
          onClick={() => onChange(item.value)}
          disabled={item.disabled}
          mod={{ active: value === item.value }}
          data-disabled={item.disabled || undefined}
        >
          <span className={cn(styles.label, classNames?.label)}>{item.label}</span>
        </UnstyledButton>
      ))}

      <FloatingIndicator
        target={controlsRefs[value]}
        parent={rootRef}
        className={cn(styles.indicator, classNames?.indicator)}
      />
    </div>
  );
}

import { Collapse, UnstyledButton } from '@mantine/core';
import { useUncontrolled } from '@mantine/hooks';
import type { PropsWithChildren, ReactNode } from 'react';
import { useId } from 'react';

import ChevronIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './Collapsible.module.css';

/**
 * Представляет свойства компонента {@link Collapsible}.
 */
export interface CollapsibleProps {
  /** Заголовок секции. */
  readonly label: ReactNode;
  /** Контент слева от заголовка (иконка, индикатор и т.д.). */
  readonly leftSection?: ReactNode;
  /** Контент справа от заголовка (кнопки, бейджи и т.д.). Не участвует в toggle. */
  readonly rightSection?: ReactNode;
  /** Контролируемое состояние раскрытости. */
  readonly opened?: boolean;
  /** Начальное состояние раскрытости (uncontrolled). */
  readonly defaultOpened?: boolean;
  /** Колбэк при переключении. Получает новое значение opened. */
  readonly onToggle?: (opened: boolean) => void;
  /** Дополнительный className для корневого элемента. */
  readonly className?: string;
  /** Блокирует раскрытие и скрывает стрелочку (например, когда нет данных). */
  readonly disabled?: boolean;
}

/**
 * Представляет компонент сворачивания/разворачивания.
 * Использует Mantine Collapse для анимации.
 * Поддерживает controlled и uncontrolled режимы.
 * Переключение срабатывает по клику на стрелку и надпись.
 */
export function Collapsible({
  label,
  leftSection,
  rightSection,
  children,
  opened,
  defaultOpened = false,
  onToggle,
  className,
  disabled,
}: PropsWithChildren<CollapsibleProps>) {
  const [isOpened, setIsOpened] = useUncontrolled({
    value: opened,
    defaultValue: defaultOpened,
    onChange: onToggle,
  });

  const contentId = useId();
  const triggerId = useId();

  const handleToggle = () => {
    if (disabled) return;
    setIsOpened(!isOpened);
  };

  return (
    <div className={cn(styles.root, className)}>
      <div className={styles.header}>
        <UnstyledButton
          id={triggerId}
          onClick={handleToggle}
          className={styles.trigger}
          aria-expanded={isOpened}
          aria-controls={contentId}
          aria-disabled={disabled ? disabled : undefined}
          data-disabled={disabled ? disabled : undefined}
        >
          <ChevronIcon
            className={styles.chevron}
            data-opened={isOpened}
            data-hidden={disabled ? disabled : undefined}
          />
          <span
            className={cn(styles.label, 'truncate')}
            title={typeof label === 'string' ? label : undefined}
          >
            {label}
          </span>
        </UnstyledButton>
        {leftSection && <div className={styles.left_section}>{leftSection}</div>}
        {rightSection && <div className={styles.right_section}>{rightSection}</div>}
      </div>

      <Collapse in={isOpened && !disabled}>
        <div
          id={contentId}
          role="region"
          aria-labelledby={triggerId}
        >
          {children}
        </div>
      </Collapse>
    </div>
  );
}

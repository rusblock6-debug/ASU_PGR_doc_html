import type { ReactNode } from 'react';

import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './MenuTargetButton.module.css';

/**
 * Представляет свойства компонента кнопки для вызова меню.
 */
interface MenuTargetButtonProps {
  /** Возвращает признак открытого меню. */
  readonly opened: boolean;
  /** Возвращает заголовок. */
  readonly label: ReactNode | string;
  /** Возвращает элемент расположенный после заголовка. */
  readonly afterLabel?: ReactNode;
  /** Возвращает класс стилей для корневого контейнера. */
  readonly rootClassName?: string;
  /** Возвращает признак неактивной кнопки. */
  readonly disabled?: boolean;
}

/**
 * Представляет компонент кнопки для вызова меню.
 */
export function MenuTargetButton(props: MenuTargetButtonProps) {
  const { opened, label, afterLabel, rootClassName, disabled = false } = props;

  return (
    <div
      className={cn(
        styles.root,
        { [styles.opened]: opened },
        { [styles.active]: !disabled },
        { [styles.disabled]: disabled },
        rootClassName,
      )}
    >
      {label}
      {afterLabel}
      <ArrowDownIcon
        className={cn(styles.arrow_icon, {
          [styles.opened]: opened,
        })}
      />
    </div>
  );
}

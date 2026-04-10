import ArrowDownIcon from '@/shared/assets/icons/ic-arrow-down.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './ResponsiveMenuButton.module.css';

/**
 * Представляет свойства компонента кнопки открытия адаптивного меню.
 */
interface ResponsiveMenuButtonProps {
  /** Состояние открытия. */
  readonly opened: boolean;
}

/**
 * Представляет компонент кнопки открытия адаптивного меню.
 */
export function ResponsiveMenuButton(props: ResponsiveMenuButtonProps) {
  const { opened } = props;

  return (
    <div className={styles.root}>
      <ArrowDownIcon className={cn(styles.arrow_icon, { [styles.opened]: opened })} />
    </div>
  );
}

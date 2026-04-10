import WarningIcon from '@/shared/assets/icons/ic-warning.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './WarningMessage.module.css';

/**
 * Представляет свойства компонента {@link WarningMessage}
 */
interface WarningMessageProps {
  /** Текст сообщения об ошибке */
  readonly message: string;
  /** Дополнительные CSS классы для кастомизации */
  readonly classNames?: string;
  /** Размер. */
  readonly size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

/**
 * Представляет компонент для отображения сообщения о предупреждении.
 */
export function WarningMessage({ message, classNames, size = 'sm' }: WarningMessageProps) {
  return (
    <div className={cn(classNames, styles.warning, styles[size])}>
      <WarningIcon
        className={styles.icon}
        width={16}
        height={16}
      />
      <p className={cn(styles.text, styles[size])}>{message}</p>
    </div>
  );
}

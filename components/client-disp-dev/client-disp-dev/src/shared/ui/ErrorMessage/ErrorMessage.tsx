import CrossCircleIcon from '@/shared/assets/icons/ic-cross-circle-fill.svg?react';
import { cn } from '@/shared/lib/classnames-utils';

import styles from './ErrorMessage.module.css';

/**
 * Представляет свойства компонента {@link ErrorMessage}
 */
interface ErrorMessageProps {
  /** Текст сообщения об ошибке */
  readonly message: string;
  /** Дополнительные CSS классы для кастомизации */
  readonly classNames?: string;
  /** Размер. */
  readonly size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

/**
 * Представляет компонент для отображения сообщения об ошибке.
 */
export function ErrorMessage({ message, classNames, size = 'sm' }: ErrorMessageProps) {
  return (
    <div className={cn(classNames, styles.error, styles[size])}>
      <CrossCircleIcon
        className={styles.icon}
        width={16}
        height={16}
      />
      <p className={cn(styles.text, styles[size])}>{message}</p>
    </div>
  );
}

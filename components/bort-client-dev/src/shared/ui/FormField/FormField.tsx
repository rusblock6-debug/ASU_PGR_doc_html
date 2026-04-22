import type { ReactNode } from 'react';
import type { FieldError } from 'react-hook-form';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './FormField.module.css';

/**
 * Обёртка поля формы: опциональный label, контент, сообщение об ошибке.
 */
export function FormField({
  label,
  error,
  children,
  className,
}: {
  readonly label?: string;
  readonly error?: FieldError;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <div className={cn(styles.root, className)}>
      {label ? <span className={styles.label}>{label}</span> : null}
      {children}
      {error?.message ? <p className={styles.error}>{error.message}</p> : null}
    </div>
  );
}

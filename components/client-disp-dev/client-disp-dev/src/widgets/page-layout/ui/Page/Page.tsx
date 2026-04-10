import type { PropsWithChildren } from 'react';

import { cn } from '@/shared/lib/classnames-utils';

import styles from './Page.module.css';

type PageProps = {
  readonly className?: string;
  /**
   * Возвращает вариант страницы.
   */
  readonly variant?: 'default' | 'table';
} & PropsWithChildren;

export function Page({ className, variant = 'default', children }: PageProps) {
  return (
    <main
      className={cn(
        styles.page_content,
        className,
        { [styles.page_default]: variant === 'default' },
        { [styles.page_table]: variant === 'table' },
      )}
    >
      {children}
    </main>
  );
}

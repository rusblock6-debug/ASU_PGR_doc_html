import type { ComponentPropsWithoutRef, ReactNode } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { AppButton } from '@/shared/ui/AppButton';
import { Tooltip } from '@/shared/ui/Tooltip';

import styles from './IconButton.module.css';

/** Свойства компонента {@link IconButton}. */
interface IconButtonProps extends ComponentPropsWithoutRef<typeof AppButton> {
  /** Иконка (передаётся через children). */
  readonly children: ReactNode;
}

/**
 * Кнопка-иконка для сайдбара карты.
 */
export function IconButton({ children, className, title, ...rest }: IconButtonProps) {
  return (
    <AppButton
      className={cn(styles.button, className)}
      size="xs"
      onlyIcon
      variant="clear"
      {...rest}
    >
      <Tooltip
        label={title}
        position="right"
      >
        {children}
      </Tooltip>
    </AppButton>
  );
}

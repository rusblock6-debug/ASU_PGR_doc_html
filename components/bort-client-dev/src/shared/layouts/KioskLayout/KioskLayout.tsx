import type { CSSProperties, ReactElement, ReactNode } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { useDocumentTitle } from '@/shared/lib/hooks/useDocumentTitle';

import styles from './KioskLayout.module.css';

/**
 * Пропсы полноэкранного kiosk-макета.
 */
interface KioskLayoutProps {
  readonly header: ReactElement;
  readonly children: ReactNode;
  readonly asideLeft?: ReactNode;
  readonly asideRight?: ReactNode;
  readonly asideLeftWidth?: string;
  readonly asideRightWidth?: string;
  readonly className?: string;
}

/**
 * Полноэкранный макет бортового клиента: шапка, контент, опциональные сайдбары управления.
 */
export const KioskLayout = ({
  header,
  children,
  asideLeft,
  asideRight,
  asideLeftWidth = '90px',
  asideRightWidth = '90px',
  className,
}: KioskLayoutProps) => {
  useDocumentTitle('АСУ ПГР — борт');

  return (
    <div
      className={cn(styles.root, className)}
      style={
        {
          '--kiosk-aside-left-width': asideLeftWidth,
          '--kiosk-aside-right-width': asideRightWidth,
        } as CSSProperties
      }
    >
      {header}
      <div className={styles.main}>
        {asideLeft ? <div className={styles.aside_left}>{asideLeft}</div> : null}
        <div className={styles.content}>{children}</div>
        {asideRight ? <div className={styles.aside_right}>{asideRight}</div> : null}
      </div>
    </div>
  );
};

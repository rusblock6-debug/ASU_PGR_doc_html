import type { ReactElement } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { useDocumentTitle } from '@/shared/lib/hooks/useDocumentTitle';

import styles from './MainLayout.module.css';

interface MainLayoutProps {
  readonly sidebar: ReactElement;
  readonly header: ReactElement;
  readonly content: ReactElement;
  readonly className?: string;
}

export function MainLayout({ sidebar, header, content, className }: MainLayoutProps) {
  useDocumentTitle('АСУ ПГР');

  return (
    <div className={cn(styles.page, className)}>
      {sidebar}

      <div className={cn(styles.body)}>
        {header}
        {content}
      </div>
    </div>
  );
}

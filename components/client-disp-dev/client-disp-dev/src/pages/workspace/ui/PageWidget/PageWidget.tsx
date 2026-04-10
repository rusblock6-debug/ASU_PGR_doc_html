import { memo, type ReactNode } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { type PinnedPage } from '@/features/pin-page';

import styles from './PageWidget.module.css';

interface PageWidgetProps {
  readonly page: PinnedPage;
  readonly children: ReactNode;
}

export const PageWidget = memo(function PageWidget({ page, children }: PageWidgetProps) {
  return (
    <Page className={styles.widget}>
      <Header routeKey={page.id} />

      <div className={styles.content}>{children}</div>
    </Page>
  );
});

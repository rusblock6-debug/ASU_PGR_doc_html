import type { ReactElement } from 'react';

import styles from './EmptyLayout.module.css';

interface DefaultLayoutProps {
  readonly content: ReactElement;
}

export function EmptyLayout({ content }: DefaultLayoutProps) {
  return <div className={styles.page}>{content}</div>;
}

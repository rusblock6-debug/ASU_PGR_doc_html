import type { ReactElement } from 'react';

import styles from './EmptyLayout.module.css';

/** Пропсы пустого layout-контейнера. */
interface DefaultLayoutProps {
  readonly content: ReactElement;
}

/** Layout без дополнительных областей. */
export function EmptyLayout({ content }: DefaultLayoutProps) {
  return <div className={styles.page}>{content}</div>;
}

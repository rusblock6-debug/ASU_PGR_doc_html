import type { PropsWithChildren } from 'react';

import styles from './MapTooltip.module.css';

/**
 * Compound component для содержимого тултипа карты.
 * Создаётся как JSX в R3F-слоях, рендерится в DOM-дереве через {@link MapTooltipOverlay}.
 */
function MapTooltipRoot({ children }: Readonly<PropsWithChildren>) {
  return <div className={styles.tooltip}>{children}</div>;
}

/**
 * Заголовок тултипа.
 */
function Title({ children }: Readonly<PropsWithChildren>) {
  return <div className={styles.tooltip_title}>{children}</div>;
}

/**
 * Контейнер для строк тултипа.
 */
function Body({ children }: Readonly<PropsWithChildren>) {
  return <div className={styles.tooltip_body}>{children}</div>;
}

/**
 * Строка «label — value» внутри {@link Body}.
 */
function Row({ label, children }: Readonly<PropsWithChildren<{ label: string }>>) {
  return (
    <>
      <span className={styles.tooltip_row_label}>{label}</span>
      <span className={styles.tooltip_row_value}>{children}</span>
    </>
  );
}

export const MapTooltip = Object.assign(MapTooltipRoot, {
  Title,
  Body,
  Row,
});

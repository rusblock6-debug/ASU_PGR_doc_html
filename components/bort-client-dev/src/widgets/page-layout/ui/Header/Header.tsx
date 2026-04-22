import type { PropsWithChildren } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { getItemAndSectionByPageKey } from '@/shared/routes/navigation';
import type { AppRouteType } from '@/shared/routes/router';

import styles from './Header.module.css';

/**
 * Представляет свойства компонента Header
 */
interface HeaderProps {
  /** Ключ маршрута для определения заголовка страницы */
  readonly routeKey: AppRouteType;
  /** Дополнительный CSS-класс для заголовка */
  readonly headerClassName?: string;
  /** Кастомное название страницы (переопределяет название из роута) */
  readonly customName?: string;
  /** Дополнительный CSS-класс для всего компонента */
  readonly className?: string;
}

/** Шапка страницы с заголовком. */
export function Header(props: PropsWithChildren<HeaderProps>) {
  const { routeKey, className, headerClassName, customName, children } = props;

  const { item } = getItemAndSectionByPageKey(routeKey);
  const name = item?.title;
  const HeaderIcon = item?.headerIcon;

  return (
    <div className={cn(styles.page_header, className)}>
      <div className={styles.page_header_wrapper}>
        <div className={styles.page_title_wrapper}>
          {HeaderIcon && <HeaderIcon className={styles.page_icon} />}
          {name && <h1 className={cn(styles.page_header_drag, headerClassName)}>{customName ?? name}</h1>}
        </div>

        {children}
      </div>
    </div>
  );
}

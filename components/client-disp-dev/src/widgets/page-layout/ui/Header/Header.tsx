import type { PropsWithChildren } from 'react';

import { PinPageButton } from '@/features/pin-page';

import { cn } from '@/shared/lib/classnames-utils';
import { useIsInWorkspace } from '@/shared/lib/workspace';
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
  /** Показывать кнопку закрепить страницу. По-умолчанию всегда true. */
  readonly showPinButton?: boolean;
}

/** Шапка страницы с заголовком и кнопкой закрепления */
export function Header(props: PropsWithChildren<HeaderProps>) {
  const { routeKey, showPinButton = true, className, headerClassName, customName, children } = props;

  const isInWorkspace = useIsInWorkspace();
  const { item } = getItemAndSectionByPageKey(routeKey);
  const name = item?.title;
  const HeaderIcon = item?.headerIcon;

  return (
    <div className={cn(styles.page_header, className)}>
      <div className={styles.page_header_wrapper}>
        <div className={styles.page_title_wrapper}>
          {HeaderIcon && <HeaderIcon className={styles.page_icon} />}
          {name && (
            <h1
              className={cn(
                styles.page_header_drag,
                isInWorkspace && styles.drag_handle,
                isInWorkspace && 'js-workspace-drag-handle',
                headerClassName,
              )}
            >
              {customName ?? name}
            </h1>
          )}
        </div>

        {children}
      </div>

      {showPinButton && <PinPageButton pageId={routeKey} />}
    </div>
  );
}

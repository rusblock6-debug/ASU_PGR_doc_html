import type { CSSProperties } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { useUserLocalStorage } from '@/shared/lib/hooks/useUserLocalStorage';
import { CircularProgress } from '@/shared/ui/CircularProgress';

import { SIDEBAR_COLLAPSED_KEY, SIDEBAR_EXPANDED_WIDTH } from '../../../config/sidebar';
import { selectIsLoading, selectLoadPercentage } from '../../../model/selectors';

import styles from './MapLoader.module.css';

/**
 * Представляет свойства компонента индикатора загрузки карты.
 */
interface MapLoaderProps {
  /** Возвращает признак отображения компонента загрузки. */
  readonly showLoader?: boolean;
}

/**
 * Показывает индикатор загрузки карты.
 *
 * Смещает визуальный центр лоадера вправо на ширину раскрытого сайдбара,
 * чтобы спиннер оставался по центру видимой области карты.
 */
export function MapLoader({ showLoader = false }: MapLoaderProps) {
  const isLoading = useAppSelector(selectIsLoading);
  const loadPercentage = useAppSelector(selectLoadPercentage);

  const [isCollapsed] = useUserLocalStorage(SIDEBAR_COLLAPSED_KEY, false);

  const style = {
    '--sidebar-offset': isCollapsed ? '0px' : `${SIDEBAR_EXPANDED_WIDTH}px`,
  } as CSSProperties;

  if (!isLoading && !showLoader) {
    return null;
  }

  return (
    <div
      className={styles.loader}
      style={style}
    >
      {hasValue(loadPercentage) ? (
        <CircularProgress value={loadPercentage} />
      ) : (
        <div className={cn(styles.loader_icon, 'loader')} />
      )}
      <div className={styles.loader_text}>Загрузка данных</div>
    </div>
  );
}

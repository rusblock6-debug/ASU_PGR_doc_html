import type { ReactNode } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { NO_DATA } from '@/shared/lib/constants';
import { formatDistance } from '@/shared/lib/format-distance';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { Tooltip } from '@/shared/ui/Tooltip';

import { Divider } from '../../../Divider';

import styles from './RouteHeader.module.css';

/**
 * Представляет свойства компонента заголовка элемента списка маршрутов в вертикальном режиме.
 */
interface RouteVerticalHeaderProps {
  /** Возвращает наименование пункта погрузки. */
  readonly routeFromTitle: string;
  /** Возвращает наименование пункта разгрузки. */
  readonly routeToTitle?: string;
  /** Возвращает плановый объем. */
  readonly volumePlan: number | null;
  /** Возвращает фактический объем. */
  readonly volumeFact: number | null;
  /** Возвращает количество оборудования на маршруте. */
  readonly vehicleCount?: number;
  /** Возвращает дистанцию. */
  readonly distance: number | null;
  /** Возвращает компонент кнопки для перемещения карточки маршрута. */
  readonly dragButton?: ReactNode;
  /** Возвращает компонент кнопки для удаления маршрута. */
  readonly removeButton: ReactNode;
}

/**
 * Представляет компонент заголовка элемента списка маршрутов в вертикальном режиме.
 */
export function RouteVerticalHeader({
  routeFromTitle,
  routeToTitle,
  volumePlan,
  volumeFact,
  vehicleCount,
  distance,
  dragButton,
  removeButton,
}: RouteVerticalHeaderProps) {
  const formatedVolumePlan = formatNumber(volumePlan, NO_DATA.DASH);
  const formatedVolumeFact = formatNumber(volumeFact, NO_DATA.DASH);
  const formatedVehicleCount = vehicleCount ?? NO_DATA.DASH;

  return (
    <>
      <div className={cn(styles.header, styles.vertical)}>
        <div className={cn(styles.title_container, styles.vertical)}>
          <Tooltip label={routeFromTitle}>
            <p className={styles.title}>{routeFromTitle}</p>
          </Tooltip>
          {hasValue(routeToTitle) && (
            <Tooltip label={routeToTitle}>
              <p className={styles.title}>
                {' — '}
                {routeToTitle}
              </p>
            </Tooltip>
          )}
        </div>
        <div className={cn(styles.actions_container, styles.vertical)}>
          {dragButton}
          {removeButton}
        </div>
      </div>
      <Divider
        height={1}
        color="var(--bg-widget-hover)"
      />
      <Tooltip
        label={
          <>
            <p className={styles.vertical_tooltip_info_string}>
              <span className={styles.info_title}>План/факт, м³</span>
              <span className={styles.info}>
                {formatedVolumePlan}/{formatedVolumeFact}
              </span>
            </p>
            <p className={styles.vertical_tooltip_info_string}>
              <span className={styles.info_title}>Техники на маршруте</span>
              <span className={styles.info}>{formatedVehicleCount} ед.</span>
            </p>
            <p className={styles.vertical_tooltip_info_string}>
              <span className={styles.info_title}>Расстояние</span>
              <span className={styles.info}>{hasValue(distance) ? formatDistance(distance) : NO_DATA.DASH}</span>
            </p>
          </>
        }
      >
        <p className={cn(styles.info, styles.vertical)}>
          {formatedVolumePlan}/{formatedVolumeFact} {formatedVehicleCount} {distance ?? NO_DATA.DASH}
        </p>
      </Tooltip>
    </>
  );
}

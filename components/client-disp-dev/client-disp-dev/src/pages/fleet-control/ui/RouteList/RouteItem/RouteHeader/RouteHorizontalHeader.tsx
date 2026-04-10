import type { ReactNode } from 'react';

import FleetControlIcon from '@/shared/assets/icons/ic-page-fleet-control.svg?react';
import { NO_DATA } from '@/shared/lib/constants';
import { formatDistance } from '@/shared/lib/format-distance';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { useCheckTextOverflow } from '@/shared/lib/hooks/useCheckTextOverflow';
import { Tooltip } from '@/shared/ui/Tooltip';

import styles from './RouteHeader.module.css';

/**
 * Представляет свойства компонента заголовка элемента списка маршрутов в горизонтальном режиме.
 */
interface RouteHorizontalHeader {
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
  /** Возвращает компонент для отображения предупреждения. */
  readonly warning?: ReactNode;
  /** Возвращает компонент для отображения ошибки. */
  readonly error?: ReactNode;
}

/**
 * Представляет компонент заголовка элемента списка маршрутов в горизонтальном режиме.
 */
export function RouteHorizontalHeader({
  routeFromTitle,
  routeToTitle,
  volumePlan,
  volumeFact,
  vehicleCount,
  distance,
  dragButton,
  removeButton,
  warning,
  error,
}: RouteHorizontalHeader) {
  const routeTitle = `${routeFromTitle}${hasValue(routeToTitle) ? ' — ' + routeToTitle : ''}`;

  const { ref, isTextOverflowed } = useCheckTextOverflow(routeTitle);

  return (
    <div className={styles.header}>
      <div className={styles.title_container}>
        <FleetControlIcon className={styles.icon} />
        <Tooltip
          label={routeTitle}
          disabled={!isTextOverflowed}
        >
          <p
            ref={ref}
            className={styles.title}
          >
            {routeTitle}
          </p>
        </Tooltip>
      </div>
      <div className={styles.info_container}>
        <div className={styles.info_item}>
          <p className={styles.info_title}>План/факт, м³</p>
          <p className={styles.info}>
            {formatNumber(volumePlan, NO_DATA.DASH)}/{formatNumber(volumeFact, NO_DATA.DASH)}
          </p>
        </div>
        <div className={styles.info_item}>
          <p className={styles.info_title}>Техники на маршруте</p>
          <p className={styles.info}>{vehicleCount ?? NO_DATA.DASH} ед.</p>
        </div>
        <div className={styles.info_item}>
          <p className={styles.info_title}>Расстояние</p>
          <p className={styles.info}>{hasValue(distance) ? formatDistance(distance) : NO_DATA.DASH}</p>
        </div>
      </div>
      <div className={styles.actions_container}>
        {(warning || error) && (
          <div className={styles.attention_container}>
            {warning}
            {error}
          </div>
        )}
        {removeButton}
        {dragButton}
      </div>
    </div>
  );
}

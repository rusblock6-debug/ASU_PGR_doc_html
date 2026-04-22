import type React from 'react';

import { cn } from '@/shared/lib/classnames-utils';

import { POINTER_HEIGHT, POINTER_WIDTH } from './gauge-geometry';
import { MovementButton } from './MovementButton';
import styles from './TripGauge.module.css';
import { useGaugeData } from './useGaugeData';

/** Пропсы виджета «план / факт рейсов» со спидометром. */
interface TripGaugeProps {
  /** Фактическое количество рейсов. */
  readonly actual: number;
  /** Плановое количество рейсов. */
  readonly planned: number;
  /** Слот в верхнем левом углу (напр. кнопка «назад»). */
  readonly topLeftAction?: React.ReactNode;
  /** Контент в левом нижнем углу (напр. таймер состояния). */
  readonly bottomLeftContent?: React.ReactNode;
  /** Плашка «ДВИЖЕНИЕ» под спидометром; на главном экране вынесена в колонку. */
  readonly withMovementButton?: boolean;
}

/** Полукруглый gauge: факт/план рейсов и опционально плашка движения. */
export const TripGauge = ({
  actual,
  planned,
  topLeftAction,
  bottomLeftContent,
  withMovementButton = true,
}: TripGaugeProps) => {
  const { displayActual, displayPlanned, filledPath, unfilledPath, ticks, pointer } = useGaugeData(actual, planned);

  return (
    <section
      className={cn(styles.root, !withMovementButton && styles.root_gauge_only)}
      aria-label="План и факт рейсов задания"
    >
      {topLeftAction ? <div className={styles.top_left}>{topLeftAction}</div> : null}

      <div className={styles.gauge_wrap}>
        <svg
          className={styles.gauge}
          viewBox="-55 -55 410 256"
          role="img"
          aria-hidden
        >
          {unfilledPath ? (
            <path
              d={unfilledPath}
              className={styles.track}
            />
          ) : null}
          {filledPath ? (
            <path
              d={filledPath}
              className={styles.track_filled}
            />
          ) : null}

          {ticks.map((t, i) => (
            <line
              key={`tick-${String(i)}`}
              x1={t.x1}
              y1={t.y1}
              x2={t.x2}
              y2={t.y2}
              className={styles.tick}
            />
          ))}

          {pointer ? (
            <g transform={`translate(${pointer.center.x}, ${pointer.center.y}) rotate(${pointer.rotation})`}>
              <rect
                x={-POINTER_WIDTH / 2}
                y={-POINTER_HEIGHT / 2}
                width={POINTER_WIDTH}
                height={POINTER_HEIGHT}
                rx="6"
                ry="6"
                className={styles.pointer}
              />
            </g>
          ) : null}
        </svg>

        <div className={styles.center}>
          <div className={styles.counter}>
            <span className={styles.actual}>{displayActual}</span>
            <span className={styles.separator}>/{displayPlanned}</span>
          </div>
          <span className={styles.label}>РЕЙСЫ ЗАДАНИЯ</span>
        </div>
      </div>

      {bottomLeftContent ? <div className={styles.bottom_left}>{bottomLeftContent}</div> : null}

      {withMovementButton ? <MovementButton /> : null}
    </section>
  );
};

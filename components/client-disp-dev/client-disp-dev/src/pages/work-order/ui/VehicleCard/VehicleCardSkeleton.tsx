import { cn } from '@/shared/lib/classnames-utils';
import { Skeleton } from '@/shared/ui/Skeleton';

import { RouteTaskSkeleton } from '../RouteTask';

import styles from './VehicleCard.module.css';

const SKELETON_CARDS_COUNT = 10;
const SKELETON_RADIUS = 8;

/**
 * Представляет скелетон списка карточек транспортных средств.
 */
export function VehicleCardSkeleton() {
  return (
    <div className="g-skeleton-fade">
      {Array.from({ length: SKELETON_CARDS_COUNT }, (_, index) => (
        <VehicleCardSkeletonItem
          key={index}
          isFirstElement={index === 0}
          isLastElement={index === SKELETON_CARDS_COUNT - 1}
        />
      ))}
    </div>
  );
}

/**
 * Представляет скелетон карточки транспортного средства.
 */
function VehicleCardSkeletonItem({
  isFirstElement,
  isLastElement,
}: {
  /** Указывает, является ли элемент первым в списке. */
  readonly isFirstElement?: boolean;
  /** Указывает, является ли элемент последним в списке. */
  readonly isLastElement?: boolean;
}) {
  return (
    <div
      className={cn(styles.vehicle_card, {
        [styles.first]: isFirstElement,
        [styles.last]: isLastElement,
      })}
    >
      {/* Иконка и название транспорта */}
      <div
        className={styles.vehicle}
        style={{ width: '100%' }}
      >
        <div className={styles.vehicle_title}>
          <Skeleton
            width={30}
            height={16}
            radius={SKELETON_RADIUS}
          />
          <Skeleton
            width={200}
            height={16}
            radius={SKELETON_RADIUS}
          />
        </div>

        {/* Информация о транспорте */}
        <div className={styles.vehicle_summary}>
          <div className={styles.summary}>
            <Skeleton
              width={63}
              height={14}
              radius={SKELETON_RADIUS}
            />
            <Skeleton
              width={100}
              height={14}
              radius={SKELETON_RADIUS}
            />
          </div>

          {Array.from({ length: 3 }, (_, index) => (
            <div
              key={index}
              className={styles.summary}
            >
              <Skeleton
                width={63}
                height={14}
                radius={SKELETON_RADIUS}
              />
              <Skeleton
                width={20}
                height={14}
                radius={SKELETON_RADIUS}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Кнопка добавления */}
      <div className={styles.vehicle_action}>
        <Skeleton
          width={24}
          height={24}
          radius={SKELETON_RADIUS}
        />
      </div>

      {/* Маршрутные задания */}
      <div className={styles.vehicle_routes}>
        <RouteTaskSkeleton />
      </div>
    </div>
  );
}

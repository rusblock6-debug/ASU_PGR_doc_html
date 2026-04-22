import { cn } from '@/shared/lib/classnames-utils';
import { Skeleton } from '@/shared/ui/Skeleton';

import styles from './RouteTask.module.css';

const SKELETON_RADIUS = 8;

/**
 * Представляет компонент скелетона карточки маршрутного задания.
 */
export function RouteTaskSkeleton() {
  return (
    <div className={styles.route_task}>
      <div className={cn(styles.route_task_header, styles.skeleton_route_task_header)}>
        <Skeleton
          width={120}
          height={20}
          radius={SKELETON_RADIUS}
        />
        <Skeleton
          width={60}
          height={20}
          radius={SKELETON_RADIUS}
        />
      </div>
      <div className={styles.route_task_body}>
        {Array.from({ length: 6 }, (_, index) => (
          <div
            key={index}
            className={cn(styles.route_task_field, styles.skeleton_task_field)}
          >
            <Skeleton
              width={90}
              height={12}
              radius={SKELETON_RADIUS}
            />
            <Skeleton
              height={22}
              radius={SKELETON_RADIUS}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

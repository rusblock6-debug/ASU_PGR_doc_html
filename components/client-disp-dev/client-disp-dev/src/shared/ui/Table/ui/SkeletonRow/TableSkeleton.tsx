import { cn } from '@/shared/lib/classnames-utils';
import { Skeleton } from '@/shared/ui/Skeleton';

import type { ColumnDef } from '../../types';

import styles from './TableSkeleton.module.css';

/** Представляет свойства компонента скелетона для таблицы. */
interface SkeletonRowProps<TData> {
  /** Возвращает список колонок. */
  readonly columns: ColumnDef<TData>[];
}

/**
 * Представляет компонент скелетона для таблицы.
 */
export function TableSkeleton<TData>({ columns }: SkeletonRowProps<TData>) {
  return (
    <tbody className={styles.skeleton_tbody}>
      {Array.from({ length: 20 }).map((_, index) => (
        <tr
          key={`skeleton-${index}`}
          className={styles.skeleton_row}
          data-skeleton
        >
          {columns.map((column, index) => {
            const columnId = 'id' in column ? column.id : `column-${index}`;
            const columnSize = column.size || 100;
            const isDummyElement = column.meta?.dummyElement;

            return (
              <td
                key={columnId}
                style={{ width: columnSize }}
                className={cn(styles.skeleton_cell, { [styles.no_border]: isDummyElement })}
              >
                <div className={styles.skeleton_cell_inner}>
                  <Skeleton
                    height={16}
                    radius="sm"
                  />
                </div>
              </td>
            );
          })}
        </tr>
      ))}
    </tbody>
  );
}

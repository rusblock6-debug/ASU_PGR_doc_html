import { useMemo } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import type { SortState } from '@/shared/lib/sort-by-field';

import type { ObjectListSortField } from '../../../../model/types';
import { SortIconButton } from '../../SortIconButton';

import styles from './ObjectList.module.css';
import type { ObjectItem } from './ObjectRow';
import { ObjectRow } from './ObjectRow';

/**
 * Представляет свойства компонента {@link ObjectList}.
 */
interface ObjectListProps {
  /** Массив объектов для отображения. */
  readonly items: readonly ObjectItem[];
  /** ID скрытых объектов для отображения состояния видимости в каждой строке. */
  readonly hiddenIds?: readonly number[];
  /** Текущее состояние сортировки. */
  readonly sortState?: SortState<ObjectListSortField>;
  /** Колбэк смены сортировки по полю. */
  readonly onSortChange?: (field: ObjectListSortField) => void;
  /** Колбэк наведения камеры на объект по id. */
  readonly onLocate?: (id: number) => void;
  /** Колбэк переключения видимости объекта на карте. */
  readonly onToggleVisibility?: (id: number) => void;
  /** Колбэк редактирования объекта. */
  readonly onEdit?: (id: number) => void;
  /** Дополнительный className для корневого элемента. */
  readonly className?: string;
}

/**
 * Табличный список объектов с grid-раскладкой.
 * Колонки «Остаток» и «Горизонт» скрываются, если в данных нет соответствующих полей.
 */
export function ObjectList({
  items,
  hiddenIds,
  sortState,
  onSortChange,
  onLocate,
  onToggleVisibility,
  onEdit,
  className,
}: ObjectListProps) {
  const { stock: hasStock, horizon: hasHorizon } = useMemo(() => deriveVisibleColumns(items), [items]);

  const gridTemplateColumns = ['auto', '1fr', hasStock && 'auto', hasHorizon && 'auto', 'auto']
    .filter(Boolean)
    .join(' ');

  const canSort = hasValue(sortState) && hasValue(onSortChange);

  return (
    <div
      className={cn(styles.list, className)}
      style={{ gridTemplateColumns }}
    >
      <div
        className={styles.header}
        role="row"
      >
        <span className={styles.header_icon} />
        <span className={styles.header_name}>
          Наименование
          {canSort && (
            <SortIconButton
              field="name"
              sortState={sortState}
              onSortChange={onSortChange}
            />
          )}
        </span>
        {hasStock && (
          <span className={styles.header_stock}>
            Остаток
            {canSort && (
              <SortIconButton
                field="stock"
                sortState={sortState}
                onSortChange={onSortChange}
              />
            )}
          </span>
        )}
        {hasHorizon && (
          <span className={styles.header_horizon}>
            Горизонт
            {canSort && (
              <SortIconButton
                field="horizon"
                sortState={sortState}
                onSortChange={onSortChange}
              />
            )}
          </span>
        )}
        <span />
      </div>

      {items.map((item) => (
        <ObjectRow
          key={item.id}
          item={item}
          hasStock={hasStock}
          hasHorizon={hasHorizon}
          hidden={hiddenIds?.includes(item.id)}
          onLocate={onLocate}
          onToggleVisibility={onToggleVisibility}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}

/**
 * Определяет, какие колонки показывать в таблице по наличию данных.
 */
function deriveVisibleColumns(items: readonly ObjectItem[]) {
  let hasStock = false;
  let hasHorizon = false;
  for (const item of items) {
    if (hasValueNotEmpty(item.stock)) hasStock = true;
    if (hasValueNotEmpty(item.horizon)) hasHorizon = true;
    if (hasStock && hasHorizon) break;
  }
  return { stock: hasStock, horizon: hasHorizon };
}

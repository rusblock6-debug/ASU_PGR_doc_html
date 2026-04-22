'use no memo';

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Header } from '@tanstack/react-table';
import { flexRender } from '@tanstack/react-table';
import type { CSSProperties } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { Tooltip } from '@/shared/ui/Tooltip';

import { getColumnMeta } from '../../lib/column-utils';

import styles from './TableHeader.module.css';

interface DraggableTableHeaderProps<TData> {
  readonly header: Header<TData, unknown>;
  readonly isLoading: boolean;
}

export function TableHeader<TData>({ header, isLoading }: DraggableTableHeaderProps<TData>) {
  const isSelectColumn = header.column.id === 'select';
  const isDummyColumn = Boolean(getColumnMeta(header)?.dummyElement);
  const isNotDraggable = isSelectColumn || isDummyColumn;
  const canResize = header.column.getCanResize();

  const { attributes, isDragging, listeners, setNodeRef, transform } = useSortable({
    id: header.column.id,
    disabled: isNotDraggable || isLoading,
  });

  const style: CSSProperties = {
    opacity: 1,
    transform: CSS.Translate.toString(transform),
    whiteSpace: 'nowrap',
    width: header.column.getSize(),
    zIndex: isDragging && !isSelectColumn ? 1 : '',
  };

  // Получаем текст заголовка для tooltip
  const headerText =
    typeof header.column.columnDef.header === 'string' ? header.column.columnDef.header : header.column.id;

  return (
    <th
      colSpan={header.colSpan}
      style={style}
      className={cn(styles.header_cell, {
        [styles.header_cell_sticky]: isSelectColumn,
      })}
    >
      <div
        ref={setNodeRef}
        className={cn(styles.header_content, {
          [styles.drag_handle]: !isNotDraggable && !isLoading,
          [styles.header_content_checkbox]: isSelectColumn,
        })}
        style={!isNotDraggable && isDragging ? { cursor: 'grabbing' } : undefined}
        {...(!isNotDraggable && !isLoading && { ...attributes, ...listeners })}
      >
        {!isSelectColumn ? (
          <Tooltip label={headerText}>
            <div className="truncate">
              {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
            </div>
          </Tooltip>
        ) : (
          <>{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</>
        )}
      </div>
      {canResize && !isLoading && (
        <button
          onMouseDown={header.getResizeHandler()}
          className={cn(styles.resizer, { [styles.is_resizing]: header.column.getIsResizing() })}
        />
      )}
    </th>
  );
}

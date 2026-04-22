'use no memo';

import type { Row } from '@tanstack/react-table';
import type { VirtualItem, Virtualizer } from '@tanstack/react-virtual';
import type { CSSProperties, MouseEvent } from 'react';
import { useRef } from 'react';

import { LoadingSpinner } from '@/shared/ui/LoadingSpinner';

import type { ColumnDef } from '../../types';
import { EmptyState } from '../EmptyState';
import { TableSkeleton } from '../SkeletonRow';
import { TableCell } from '../TableCell';

import styles from './TableBody.module.css';

interface TableBodyProps<TData> {
  readonly rows: Row<TData>[];
  readonly rowVirtualizer: Virtualizer<HTMLDivElement, Element>;
  readonly virtualRows: VirtualItem[];
  readonly isLoading: boolean;
  readonly columns: ColumnDef<TData>[];
}

export function TableBody<TData>({ rows, rowVirtualizer, virtualRows, isLoading, columns }: TableBodyProps<TData>) {
  const tbodyRef = useRef<HTMLTableSectionElement>(null);

  const handleCellMouseEnter = (event: MouseEvent<HTMLTableSectionElement>) => {
    const target = event.target as HTMLElement;
    const cell = target.closest('td');
    if (cell && tbodyRef.current) {
      const columnIndex = cell.getAttribute('data-column-index');
      if (columnIndex !== null) {
        const prevHovered = tbodyRef.current.querySelectorAll('.js-column-hovered');
        prevHovered.forEach((el) => el.classList.remove('js-column-hovered'));

        const columnCells = tbodyRef.current.querySelectorAll(`td[data-column-index="${columnIndex}"]`);
        columnCells.forEach((el) => el.classList.add('js-column-hovered'));
      }
    }
  };

  const handleCellMouseLeave = () => {
    if (tbodyRef.current) {
      const hovered = tbodyRef.current.querySelectorAll('.js-column-hovered');
      hovered.forEach((el) => el.classList.remove('js-column-hovered'));
    }
  };

  const paddingTop = virtualRows.length > 0 ? (virtualRows[0]?.start ?? 0) : 0;
  const paddingBottom =
    virtualRows.length > 0 ? rowVirtualizer.getTotalSize() - (virtualRows[virtualRows.length - 1]?.end ?? 0) : 0;

  const showSkeleton = rows.length === 0 && isLoading;
  const showEmptyState = rows.length === 0 && !isLoading;
  const showLoadingSpinner = rows.length > 0 && isLoading;

  if (showSkeleton) {
    return <TableSkeleton columns={columns} />;
  }

  if (showEmptyState) {
    return <EmptyState columnsCount={columns.length} />;
  }

  return (
    <tbody
      ref={tbodyRef}
      className={styles.tbody}
      style={{
        height: `${rowVirtualizer.getTotalSize()}px`,
      }}
      onMouseEnter={handleCellMouseEnter}
      onMouseMove={handleCellMouseEnter}
      onMouseLeave={handleCellMouseLeave}
    >
      {paddingTop > 0 && (
        <tr
          className={styles.padding_row}
          style={{
            height: `${paddingTop}px`,
          }}
        />
      )}
      {virtualRows.map((virtualRow) => {
        const row = rows[virtualRow.index];

        return (
          <tr
            key={row.id}
            className={styles.virtual_row}
            data-selected={row.getIsSelected() || undefined}
            style={
              {
                transform: `translateY(${virtualRow.start}px)`,
                '--bg-table-row': virtualRow.index % 2 === 0 ? 'var(--orem-bw-800)' : 'var(--bg-widget)',
                '--bg-table-row-hover': virtualRow.index % 2 === 0 ? 'var(--orem-bw-600)' : 'var(--orem-bw-700)',
              } as CSSProperties
            }
          >
            {row.getVisibleCells().map((cell, cellIndex) => (
              <TableCell
                key={cell.id}
                cell={cell}
                columnIndex={cellIndex}
              />
            ))}
          </tr>
        );
      })}
      {paddingBottom > 0 && (
        <tr
          className={styles.padding_row}
          style={{
            height: `${paddingBottom}px`,
          }}
        />
      )}
      {showLoadingSpinner && (
        <tr className={styles.loading_row}>
          <td className={styles.loading_cell}>
            <LoadingSpinner />
          </td>
        </tr>
      )}
    </tbody>
  );
}

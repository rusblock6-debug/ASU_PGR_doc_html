'use no memo';

import { getCoreRowModel, useReactTable } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { type ReactNode, useEffect, useMemo, useRef, useState } from 'react';

import { cn } from '@/shared/lib/classnames-utils';
import { hasValueNotEmpty } from '@/shared/lib/has-value';

import { useColumnOrder } from '../../lib/hooks/useColumnOrder';
import { useTableContext } from '../../model/TableContext';
import type { ColumnDef } from '../../types';
import { CheckboxCell } from '../CheckboxCell';
import { NativeCheckbox } from '../NativeCheckbox';
import { RecordDrawer } from '../RecordDrawer';
import { TableBody } from '../TableBody';
import { TableContainer } from '../TableContainer';
import { TableHead } from '../TableHead';

import styles from './TableSimple.module.css';

export interface TableProps<TData> {
  readonly data?: readonly TData[];
  readonly columns?: ColumnDef<TData>[];
  readonly className?: string;
  readonly isLoading?: boolean;
  readonly estimatedRowHeight?: number;
  readonly onScrollToBottom?: () => void;
  /** Ключ для сброса позиции скролла. При изменении скролл сбрасывается наверх. */
  readonly scrollResetKey?: string | number | null;
  readonly customDrawer?: ReactNode;
}

export function Table<TData>({
  data,
  columns,
  className,
  isLoading,
  estimatedRowHeight = 24,
  onScrollToBottom,
  scrollResetKey,
  customDrawer,
}: TableProps<TData>) {
  const context = useTableContext<TData>();

  const [rowSelection, setRowSelection] = useState({});
  const [columnSizing, setColumnSizing] = useState<Record<string, number>>({});

  useEffect(() => {
    if (context?.selectedRows.length === 0 && Object.keys(rowSelection).length > 0) {
      setRowSelection({});
    }
  }, [context?.selectedRows, rowSelection]);

  useEffect(() => {
    if (!context?.storageKey) return;

    const stored = localStorage.getItem(`${context.storageKey}-column-sizing`);
    if (stored) {
      const parsed = JSON.parse(stored) as Record<string, number>;
      setColumnSizing(parsed);
    }
  }, [context?.storageKey]);

  const allColumns = useMemo(() => {
    const selectColumn: ColumnDef<TData> = {
      id: 'select',
      header: ({ table }) => (
        <NativeCheckbox
          checked={table.getIsAllRowsSelected()}
          indeterminate={table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()}
          onChange={table.getToggleAllRowsSelectedHandler()}
        />
      ),
      cell: ({ row }) => (
        <CheckboxCell
          checked={row.getIsSelected()}
          disabled={!row.getCanSelect()}
          onChange={row.getToggleSelectedHandler()}
        />
      ),
      size: 32,
      minSize: 32,
      maxSize: 32,
      enableResizing: false,
      enableSorting: false,
      meta: {
        isCustomCell: true,
      },
    };

    const test: ColumnDef<TData> = {
      id: 'dummyColumn',
      header: () => null,
      cell: () => null,
      size: 50,
      minSize: 50,
      maxSize: 50,
      enableResizing: false,
      enableSorting: false,
      meta: {
        dummyElement: true,
      },
    };

    return [selectColumn, ...(columns ?? []), test];
  }, [columns]);

  const tableData = useMemo(() => (data ? Array.from(data) : []), [data]);

  const table = useReactTable({
    data: tableData,
    columns: allColumns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      rowSelection,
      columnSizing,
      columnVisibility: {
        dummyColumn: false,
      },
    },
    enableRowSelection: true,
    enableColumnResizing: true,
    enableSorting: false,
    columnResizeMode: 'onChange',
    columnResizeDirection: 'ltr',
    onRowSelectionChange: (updater) => {
      setRowSelection(updater);

      if (context?.onRowSelectionChange) {
        const newSelection = typeof updater === 'function' ? updater(rowSelection) : updater;
        context.onRowSelectionChange(newSelection);
      }
    },
    onColumnSizingChange: (updater) => {
      const newSizing = typeof updater === 'function' ? updater(columnSizing) : updater;
      setColumnSizing(newSizing);

      if (context?.storageKey) {
        localStorage.setItem(`${context.storageKey}-column-sizing`, JSON.stringify(newSizing));
      }
    },
    defaultColumn: {
      size: 100,
      minSize: 100,
      maxSize: 800,
    },
  });

  const initialColumnIds = table.getAllLeafColumns().map((col) => col.id);
  const { columnOrder, handleDragEnd } = useColumnOrder(initialColumnIds, context?.storageKey);

  // Обновляем порядок колонок в таблице
  useEffect(() => {
    table.setColumnOrder(columnOrder);
  }, [columnOrder, table]);

  const { rows } = table.getRowModel();
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Сброс скролла на верх таблицы
  useEffect(() => {
    if (hasValueNotEmpty(scrollResetKey) && tableContainerRef.current) {
      tableContainerRef.current.scrollTop = 0;
    }
  }, [scrollResetKey]);

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    estimateSize: () => estimatedRowHeight,
    getScrollElement: () => tableContainerRef.current,
    overscan: 5,
    onChange: (instance) => {
      const lastItem = instance.getVirtualItems()[instance.getVirtualItems().length - 1];
      if (!lastItem) return;

      if (lastItem.index >= rows.length - 1) {
        onScrollToBottom?.();
      }
    },
  });

  const virtualRows = rowVirtualizer.getVirtualItems();

  return (
    <TableContainer
      className={className}
      handleDragEnd={handleDragEnd}
      tableContainerRef={tableContainerRef}
    >
      <table
        className={cn('asu-gtk-table', styles.table)}
        style={{ width: table.getCenterTotalSize() }}
      >
        <TableHead
          table={table}
          columnOrder={columnOrder}
          isLoading={isLoading ?? false}
        />
        <TableBody
          rows={rows}
          rowVirtualizer={rowVirtualizer}
          virtualRows={virtualRows}
          isLoading={isLoading ?? false}
          columns={allColumns}
        />
      </table>

      {customDrawer || <RecordDrawer />}
    </TableContainer>
  );
}

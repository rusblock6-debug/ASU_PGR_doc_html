'use no memo';

import { horizontalListSortingStrategy, SortableContext } from '@dnd-kit/sortable';
import type { Table } from '@tanstack/react-table';

import { TableHeader } from '../TableHeader';

import styles from './TableHead.module.css';

interface TableHeadProps<TData> {
  readonly table: Table<TData>;
  readonly columnOrder: string[];
  readonly isLoading: boolean;
}

export function TableHead<TData>({ table, columnOrder, isLoading }: TableHeadProps<TData>) {
  return (
    <thead className={styles.thead}>
      {table.getHeaderGroups().map((headerGroup) => (
        <tr
          key={headerGroup.id}
          className={styles.header_row}
        >
          <SortableContext
            items={columnOrder}
            strategy={horizontalListSortingStrategy}
          >
            {headerGroup.headers.map((header) => (
              <TableHeader
                key={header.id}
                header={header}
                isLoading={isLoading}
              />
            ))}
          </SortableContext>
        </tr>
      ))}
    </thead>
  );
}

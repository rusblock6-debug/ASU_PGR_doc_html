'use no memo';

import { type Cell } from '@tanstack/react-table';

import { cn } from '@/shared/lib/classnames-utils';

import { getColumnMeta } from '../../lib/column-utils';
import { useTableContext } from '../../model/TableContext';
import { ColumnDataTypes } from '../../types';

import { CellContent } from './CellContent';
import styles from './TableCell.module.css';

interface TableCellProps<TData> {
  /** Объект ячейки из TanStack Table. */
  readonly cell: Cell<TData, unknown>;
  /** Индекс колонки для атрибута data-column-index. */
  readonly columnIndex: number;
}

/** Ячейка таблицы с поддержкой кастомного рендера, тултипа и выравнивания. */
export function TableCell<TData>({ cell, columnIndex }: TableCellProps<TData>) {
  const context = useTableContext<TData>();
  const meta = getColumnMeta(cell);
  const isDummyElement = meta?.dummyElement;
  const isSelectColumn = cell.column.id === 'select';
  const dataType = meta?.dataType;
  const isCustomCell = meta?.isCustomCell;
  const showTitle = meta?.showTitle;
  const customCell = cell.column.columnDef.cell;
  const width = cell.column.getSize();

  const handleDoubleClick = () => {
    if (isDummyElement || isSelectColumn) {
      return;
    }

    if (context?.openEditDrawer) {
      const rowData = cell.row.original;
      context.openEditDrawer(rowData);
    }
  };

  let align = meta?.align;
  if (!align) {
    switch (dataType) {
      case ColumnDataTypes.NUMBER:
      case ColumnDataTypes.DATE:
      case ColumnDataTypes.DATETIME:
      case ColumnDataTypes.TIME:
        align = 'right';
        break;
      default:
        align = 'left';
    }
  }

  return (
    <td
      style={{ width: width }}
      className={cn(styles.cell, {
        [styles.no_border]: isDummyElement,
        [styles.cell_sticky]: isSelectColumn,
      })}
      data-column-index={!isSelectColumn && !isDummyElement ? columnIndex : undefined}
      data-select={isSelectColumn || undefined}
      onDoubleClick={handleDoubleClick}
    >
      <div
        className={cn(styles.cell_inner, 'truncate', {
          [styles.align_left]: align === 'left',
          [styles.align_right]: align === 'right',
        })}
      >
        <CellContent
          customCell={customCell}
          cellContext={cell.getContext()}
          value={cell.getValue()}
          dataType={dataType}
          width={width}
          isCustomCell={isCustomCell}
          showTitle={showTitle}
        />
      </div>
    </td>
  );
}

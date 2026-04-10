'use no memo';

import { type Cell, type CellContext, flexRender } from '@tanstack/react-table';

import { Tooltip } from '@/shared/ui/Tooltip';

import { formatValue } from '../../lib/formatters';
import type { ColumnDataType } from '../../types';

const MIN_TEXT_LENGTH_FOR_TOOLTIP = 13;
const MAX_COLUMN_WIDTH_FOR_TOOLTIP = 265;

/**
 * Свойства компонента CellContent для рендеринга содержимого ячейки таблицы.
 */
interface CellContentProps<TData> {
  /** Кастомный рендерер ячейки из columnDef. */
  readonly customCell: Cell<TData, unknown>['column']['columnDef']['cell'];
  /** Контекст ячейки для передачи в flexRender. */
  readonly cellContext: CellContext<TData, unknown>;
  /** Значение ячейки. */
  readonly value: unknown;
  /** Тип данных колонки для форматирования. */
  readonly dataType?: ColumnDataType;
  /** Ширина колонки для определения показывать тултип и нет. */
  readonly width: number;
  /** Флаг кастомной ячейки. */
  readonly isCustomCell?: boolean;
  /** Признак отображения стандартного 'title' вместо 'Tooltip'. */
  readonly showTitle?: boolean;
}

/**
 * Содержимое ячейки таблицы.
 * Рендерит кастомную ячейку, текст с тултипом или простой текст.
 */
export function CellContent<TData>({
  customCell,
  cellContext,
  value,
  dataType,
  width,
  isCustomCell,
  showTitle = false,
}: CellContentProps<TData>) {
  if (isCustomCell) {
    return <>{flexRender(customCell, cellContext)}</>;
  }

  const formattedValue = formatValue(value, dataType);
  const showTooltip =
    formattedValue.length > MIN_TEXT_LENGTH_FOR_TOOLTIP && width < MAX_COLUMN_WIDTH_FOR_TOOLTIP && !showTitle;

  if (showTooltip) {
    return (
      <Tooltip label={formattedValue}>
        <span>{formattedValue}</span>
      </Tooltip>
    );
  }

  return <span title={showTitle ? formattedValue : undefined}>{formattedValue}</span>;
}

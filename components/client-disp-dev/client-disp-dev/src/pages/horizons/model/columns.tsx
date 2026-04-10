import type { Horizon } from '@/shared/api/endpoints/horizons';
import { NUMBER_VALIDATION } from '@/shared/lib/validation';
import { ColumnDataTypes, ColorCell, type ColumnDef, type EditableSelectHandlers } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/**
 * Возвращает колонки для таблицы.
 *
 * @param shaftsOptions опции шахт.
 */
export function getColumns(shaftsOptions: { selectOptions: SelectOption[]; handlers: EditableSelectHandlers }) {
  return [
    {
      header: 'Горизонт',
      accessorKey: 'name',
      accessorFn: (row) => row.name,
      size: 2000,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Высота',
      accessorKey: 'height',
      accessorFn: (row) => row.height,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: NUMBER_VALIDATION,
      },
    },
    {
      header: 'Шахта',
      accessorKey: 'shafts',
      accessorFn: (row) => row.shafts.map((item) => item.name).join(', '),
      size: 190,
      meta: {
        dataType: ColumnDataTypes.MULTI_SELECT,
        options: shaftsOptions.selectOptions,
        handlers: shaftsOptions.handlers,
      },
    },
    {
      header: 'Цвет',
      accessorKey: 'color',
      accessorFn: (row) => row.color,
      cell: ({ row }) => {
        const color = row.original.color;
        return <ColorCell color={color} />;
      },
      size: 190,
      meta: {
        dataType: ColumnDataTypes.COLOR,
        isCustomCell: true,
      },
    },
  ] as const satisfies ColumnDef<Horizon>[];
}

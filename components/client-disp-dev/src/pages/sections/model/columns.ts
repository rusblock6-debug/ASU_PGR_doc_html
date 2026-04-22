import type { Section } from '@/shared/api/endpoints/sections';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/**
 * Возвращает колонки для таблицы.
 *
 * @param horizonsSelectorOptions Опции для селектора горизонтов.
 */
export function getColumns(horizonsSelectorOptions: SelectOption[]) {
  return [
    {
      header: 'Наименование подразделения',
      accessorKey: 'name',
      accessorFn: (row) => row.name,
      size: 400,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Является подрядной организацией',
      accessorKey: 'is_contractor_organization',
      accessorFn: (row) => (row.is_contractor_organization ? 'Да' : 'Нет'),
      size: 190,
      meta: {
        dataType: ColumnDataTypes.SELECT,
        options: [
          { value: 'true', label: 'Да' },
          { value: 'false', label: 'Нет' },
        ],
        valueType: 'boolean',
      },
    },
    {
      header: 'Включает в себя',
      accessorKey: 'horizons',
      accessorFn: (row) => row.horizons.map((item) => item.name).join(', '),
      size: 400,
      meta: {
        dataType: ColumnDataTypes.MULTI_SELECT,
        options: horizonsSelectorOptions,
      },
    },
  ] as const satisfies ColumnDef<Section>[];
}

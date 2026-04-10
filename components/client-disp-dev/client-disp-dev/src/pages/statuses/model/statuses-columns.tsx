import type { Status } from '@/shared/api/endpoints/statuses';
import { ColorCell, ColumnDataTypes, type ColumnDef, type EditableSelectHandlers } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/**
 * Возвращает колонки для таблицы.
 *
 * @param organizationCategoryOptions опции организационных категорий.
 * @param analyticCategoryOptions  опции аналитических категорий.
 */
export function statusesColumns(
  organizationCategoryOptions: { selectOptions: readonly SelectOption[]; handlers: EditableSelectHandlers },
  analyticCategoryOptions: readonly SelectOption[],
) {
  return [
    {
      header: 'Наименование статуса',
      accessorKey: 'display_name',
      accessorFn: (row) => row.display_name,
      size: 190,
    },
    {
      header: 'Организационная категория',
      accessorKey: 'organization_category_id',
      accessorFn: (row) => row.organization_category_name,
      size: 220,
      meta: {
        dataType: ColumnDataTypes.EDITABLE_SELECT,
        options: organizationCategoryOptions.selectOptions,
        handlers: organizationCategoryOptions.handlers,
        valueType: 'number',
      },
    },
    {
      header: 'Аналитическая категория',
      accessorKey: 'analytic_category',
      accessorFn: (row) => row.analytic_category_display_name,
      size: 250,
      meta: {
        dataType: ColumnDataTypes.SELECT,
        options: analyticCategoryOptions,
        valueType: 'string',
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
    {
      header: 'Является рабочим статусом',
      accessorKey: 'is_work_status',
      accessorFn: (row) => (row.is_work_status ? 'Да' : 'Нет'),
      size: 250,
      meta: {
        required: false,
        valueType: 'boolean',
        dataType: ColumnDataTypes.SELECT,
        options: [
          { value: 'true', label: 'Да' },
          { value: 'false', label: 'Нет' },
        ],
      },
    },
  ] as const satisfies ColumnDef<Status>[];
}

import type { Role } from '@/shared/api/endpoints/roles';
import { dictionaryNavLinks } from '@/shared/routes/navigation';
import { isAppRoute } from '@/shared/routes/router';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';

/**
 * Возвращает колонки для таблицы.
 */
export function getColumns() {
  return [
    {
      header: 'Имя роли',
      accessorKey: 'name',
      accessorFn: (row) => row.name,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Доступные формы-функции',
      accessorKey: 'permissions_names',
      accessorFn: (row) =>
        row.permissions
          ?.map(
            (item) =>
              `${isAppRoute(item.name) ? dictionaryNavLinks.get(item.name) : item.name} (${item.can_edit ? 'редактирование' : 'просмотр'})`,
          )
          .join(', '),
      size: 600,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        showTitle: true,
      },
    },
  ] as const satisfies ColumnDef<Role>[];
}

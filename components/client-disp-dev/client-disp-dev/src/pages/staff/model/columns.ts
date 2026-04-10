import type { Staff } from '@/shared/api/endpoints/staff';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/**
 * Возвращает колонки для таблицы.
 *
 * @param rolesSelectorOptions опции для селектора ролей.
 * @param staffPositions список должностей.
 * @param staffDepartments список подразделений.
 */
export function getColumns(
  rolesSelectorOptions: readonly SelectOption[],
  staffPositions: readonly string[],
  staffDepartments: readonly string[],
) {
  return [
    {
      header: 'Имя',
      accessorKey: 'name',
      accessorFn: (row) => row.name,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Фамилия',
      accessorKey: 'surname',
      accessorFn: (row) => row.surname,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Отчество',
      accessorKey: 'patronymic',
      accessorFn: (row) => row.patronymic,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        required: false,
      },
    },
    {
      header: 'Дата рождения',
      accessorKey: 'birth_date',
      accessorFn: (row) => row.birth_date,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.DATE,
        required: false,
      },
    },
    {
      header: 'Телефон',
      accessorKey: 'phone',
      accessorFn: (row) => row.phone,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        required: false,
      },
    },
    {
      header: 'Почта',
      accessorKey: 'email',
      accessorFn: (row) => row.email,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        required: false,
      },
    },
    {
      header: 'Логин',
      accessorKey: 'username',
      accessorFn: (row) => row.username,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Пароль',
      accessorKey: 'password',
      accessorFn: () => '******',
      size: 190,
      meta: {
        dataType: ColumnDataTypes.PASSWORD,
      },
    },
    {
      header: 'Должность',
      accessorKey: 'position',
      accessorFn: (row) => row.position,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.AUTOCOMPLETE_TEXT,
        required: false,
        options: staffPositions,
      },
    },
    {
      header: 'Подразделение',
      accessorKey: 'department',
      accessorFn: (row) => row.department,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.AUTOCOMPLETE_TEXT,
        required: false,
        options: staffDepartments,
      },
    },
    {
      header: 'Табельный номер',
      accessorKey: 'personnel_number',
      accessorFn: (row) => row.personnel_number,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Роль',
      accessorKey: 'role_id',
      accessorFn: (row) => row.role_name,
      size: 190,
      meta: {
        dataType: ColumnDataTypes.SELECT,
        options: rolesSelectorOptions,
        valueType: 'number',
      },
    },
  ] as const satisfies ColumnDef<Staff>[];
}

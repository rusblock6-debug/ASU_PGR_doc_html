import type { LoadTypeCategory } from '@/shared/api/endpoints/load-type-categories';
import type { LoadType } from '@/shared/api/endpoints/load-types';
import { POSITIVE_NUMBER_VALIDATION } from '@/shared/lib/validation';
import { ColorCell, ColumnDataTypes, type ColumnDef, type EditableSelectHandlers } from '@/shared/ui/Table';

/**
 * Плоская структура данных вида груза для отображения в таблице.
 * Расширяет `LoadType`, вынося поле `is_mineral` из вложенной структуры `category` на верхний уровень.
 */
export type CargoTableData = LoadType & {
  /** Является ли данная категория полезным ископаемым. */
  readonly is_mineral: boolean;
};

/**
 * Преобразует данные вида груза в плоскую структуру для таблицы.
 * Выносит вложенные поля из `category` на верхний уровень и нормализует данные.
 *
 * @param cargo Исходный вид груза с вложенной структурой `category`.
 * @returns Плоская структура данных для отображения в таблице.
 */
export function transformCargoToTableData(cargo: LoadType): CargoTableData {
  return {
    ...cargo,
    is_mineral: cargo.category.is_mineral,
  };
}

/** Опции для настройки колонок таблицы видов грузов. */
interface ColumnsOptions {
  /** Список категорий видов грузов для выпадающего списка. */
  cargoCategories: readonly LoadTypeCategory[];
  /** Обработчики событий для редактируемого поля выбора категории. */
  cargoCategoriesHandlers: Readonly<EditableSelectHandlers>;
}

/** Создает конфигурацию колонок для таблицы видов грузов. */
export function cargoColumns(options: ColumnsOptions) {
  return [
    {
      header: 'Наименование вида груза',
      accessorKey: 'name',
      size: 200,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Категория вида груза',
      accessorKey: 'category_id',
      accessorFn: (row) => row.category.name,
      size: 200,
      meta: {
        dataType: ColumnDataTypes.EDITABLE_SELECT,
        options: options.cargoCategories.map((model) => ({
          value: String(model.id),
          label: model.name,
        })),
        handlers: options.cargoCategoriesHandlers,
        valueType: 'number',
        autoFill: Object.fromEntries(
          options.cargoCategories.map((category) => [
            String(category.id),
            {
              is_mineral: category.is_mineral,
            },
          ]),
        ),
      },
    },
    {
      header: 'Плотность, кг/м³',
      accessorKey: 'density',
      size: 200,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: POSITIVE_NUMBER_VALIDATION,
      },
    },
    {
      header: 'Является полезным ископаемым',
      accessorKey: 'is_mineral',
      accessorFn: (row) => (row.is_mineral ? 'Да' : 'Нет'),
      size: 260,
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
  ] as const satisfies ColumnDef<CargoTableData>[];
}

import type { Place, PlaceType } from '@/shared/api/endpoints/places';
import { assertNever } from '@/shared/lib/assert-never';
import { hasValue } from '@/shared/lib/has-value';
import { ZERO_POSITIVE_NUMBER_VALIDATION } from '@/shared/lib/validation';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/** Представляет строку таблицы мест с дополнительными полями для отображения. */
export type PlaceTableRow = Place & {
  /** Наименование вида груза. */
  readonly cargo_name: string;
  /** Наименование горизонта. */
  readonly horizon_name: string;
};

/**
 * Возвращает опции типов мест для выпадающего списка в зависимости от типа места.
 *
 * @param placeType Тип места для определения доступных опций.
 * @returns Массив опций типов мест.
 */
function getPlaceTypeOptions(placeType: PlaceType) {
  switch (placeType) {
    case 'load':
      return [{ value: 'load', label: 'Место погрузки' }];
    case 'unload':
    case 'reload':
      return [
        { value: 'unload', label: 'Место разгрузки' },
        { value: 'reload', label: 'Место перегрузки' },
      ];
    case 'park':
    case 'transit':
      return [
        { value: 'park', label: 'Место стоянки' },
        { value: 'transit', label: 'Транзитное место' },
      ];
    default:
      assertNever(placeType);
  }
}

/**
 * Возвращает определение колонки типа места.
 *
 * @param placeType Тип места для настройки колонки.
 * @returns Определение колонки типа места.
 */
function getPlaceTypeColumn(placeType: PlaceType) {
  return {
    header: 'Тип места',
    accessorKey: 'type',
    accessorFn: (row) => getPlaceTypeDisplayName(row.type),
    size: 190,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: getPlaceTypeOptions(placeType),
      readOnly: placeType === 'load',
      hideOnCreate: placeType === 'load',
      required: placeType !== 'load',
      valueType: 'string',
    },
  } satisfies ColumnDef<PlaceTableRow>;
}

/**
 * Возвращает определение колонки горизонта.
 *
 * @param horizonsOptions Опции горизонтов для выпадающего списка.
 * @returns Определение колонки горизонта.
 */
function getHorizonColumn(horizonsOptions: readonly SelectOption[]) {
  return {
    header: 'Горизонт',
    accessorKey: 'horizon_id',
    accessorFn: (row) => row.horizon_name,
    size: 190,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: horizonsOptions,
      required: false,
      valueType: 'number',
    },
  } satisfies ColumnDef<PlaceTableRow>;
}

/**
 * Возвращает определение колонки вида груза.
 *
 * @param cargoOptions Опции видов груза для выпадающего списка.
 * @returns Определение колонки вида груза.
 */
function getCargoColumns(cargoOptions: readonly SelectOption[]) {
  return {
    header: 'Вид груза',
    accessorKey: 'cargo_type',
    accessorFn: (row) => row.cargo_name,
    size: 190,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: cargoOptions,
      required: false,
      valueType: 'number',
    },
  } satisfies ColumnDef<PlaceTableRow>;
}

const LOCATION_COLUMN = {
  header: 'Местоположение',
  accessorKey: 'location',
  accessorFn: (row) =>
    hasValue(row.location?.lon) && hasValue(row.location?.lat) ? `${row.location.lat}, ${row.location.lon}` : null,
  size: 190,
  meta: {
    dataType: ColumnDataTypes.COORDINATES,
    required: false,
  },
} satisfies ColumnDef<PlaceTableRow>;

const START_DATE_COLUMN = {
  header: 'Дата начала эксплуатации',
  accessorKey: 'start_date',
  accessorFn: (row) => ('start_date' in row ? row.start_date : null),
  size: 190,
  meta: {
    dataType: ColumnDataTypes.DATE,
    required: false,
    columnWithMaxValue: 'end_date',
  },
} satisfies ColumnDef<PlaceTableRow>;

const END_DATE_COLUMN = {
  header: 'Дата конца эксплуатации',
  accessorKey: 'end_date',
  accessorFn: (row) => ('end_date' in row ? row.end_date : null),
  size: 190,
  meta: {
    dataType: ColumnDataTypes.DATE,
    required: false,
    columnWithMinValue: 'start_date',
  },
} satisfies ColumnDef<PlaceTableRow>;

const UPDATED_AT_COLUMN = {
  header: 'Дата изменения',
  accessorKey: 'updated_at',
  accessorFn: (row) => row.updated_at,
  size: 190,
  meta: {
    dataType: ColumnDataTypes.DATE,
    readOnly: true,
    hideOnCreate: true,
    required: false,
  },
} satisfies ColumnDef<PlaceTableRow>;

/**
 * Возвращает отображаемое название типа места.
 *
 * @param placeType Тип места для получения названия.
 * @returns Отображаемое название типа места.
 */
function getPlaceTypeDisplayName(placeType: PlaceType) {
  switch (placeType) {
    case 'load':
      return 'Место погрузки';
    case 'unload':
      return 'Место разгрузки';
    case 'reload':
      return 'Место перегрузки';
    case 'transit':
      return 'Транзитное место';
    case 'park':
      return 'Место стоянки';
    default:
      assertNever(placeType);
  }
}

/**
 * Возвращает колонки для таблицы.
 *
 * @param placeType тип места.
 * @param horizonsOptions опции горизонтов.
 * @param cargoOptions опции видов груза.
 */
export function getColumns(
  placeType: PlaceType,
  horizonsOptions: readonly SelectOption[],
  cargoOptions: readonly SelectOption[],
): readonly ColumnDef<PlaceTableRow>[] {
  switch (placeType) {
    case 'load':
      return [
        {
          header: 'Наименование ПП',
          accessorKey: 'name',
          accessorFn: (row) => row.name,
          size: 190,
          meta: {
            dataType: ColumnDataTypes.TEXT,
          },
        } satisfies ColumnDef<PlaceTableRow>,
        getPlaceTypeColumn(placeType),
        LOCATION_COLUMN,
        START_DATE_COLUMN,
        END_DATE_COLUMN,
        {
          header: 'Остаток, м³',
          accessorKey: 'current_stock',
          accessorFn: (row) => ('current_stock' in row ? row.current_stock : null),
          size: 190,
          meta: {
            dataType: ColumnDataTypes.NUMBER,
            required: false,
            validation: ZERO_POSITIVE_NUMBER_VALIDATION,
          },
        },
        getHorizonColumn(horizonsOptions),
        getCargoColumns(cargoOptions),
        UPDATED_AT_COLUMN,
      ];
    case 'unload':
    case 'reload':
      return [
        {
          header: 'Наименование ПР',
          accessorKey: 'name',
          accessorFn: (row) => row.name,
          size: 190,
          meta: {
            dataType: ColumnDataTypes.TEXT,
          },
        },
        getPlaceTypeColumn(placeType),
        LOCATION_COLUMN,
        START_DATE_COLUMN,
        END_DATE_COLUMN,
        {
          header: 'Вместимость, м³',
          accessorKey: 'capacity',
          accessorFn: (row) => ('capacity' in row ? row.capacity : null),
          size: 190,
          meta: {
            dataType: ColumnDataTypes.NUMBER,
            required: false,
            validation: ZERO_POSITIVE_NUMBER_VALIDATION,
          },
        },
        {
          header: 'Остаток, м³',
          accessorKey: 'current_stock',
          accessorFn: (row) => ('current_stock' in row ? row.current_stock : null),
          size: 190,
          meta: {
            dataType: ColumnDataTypes.NUMBER,
            required: false,
            validation: ZERO_POSITIVE_NUMBER_VALIDATION,
          },
        },
        getHorizonColumn(horizonsOptions),
        getCargoColumns(cargoOptions),
        UPDATED_AT_COLUMN,
      ];
    case 'transit':
    case 'park':
      return [
        {
          header: 'Наименование',
          accessorKey: 'name',
          accessorFn: (row) => row.name,
          // Для того чтобы по умолчанию колонка имела максимально возможную ширину.
          size: 2000,
          meta: {
            dataType: ColumnDataTypes.TEXT,
          },
        },
        getPlaceTypeColumn(placeType),
        LOCATION_COLUMN,
        getHorizonColumn(horizonsOptions),
      ];
    default:
      assertNever(placeType);
  }
}

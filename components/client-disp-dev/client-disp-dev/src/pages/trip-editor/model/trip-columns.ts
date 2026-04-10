import type { EnrichedTrip } from '@/shared/api/endpoints/trips';
import { hasValue } from '@/shared/lib/has-value';
import { DATE_VALIDATION, POSITIVE_NUMBER_VALIDATION, validateDateRange } from '@/shared/lib/validation';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';
import type { SelectOption } from '@/shared/ui/types';

/**
 * Возвращает колонки для таблицы рейсов.
 *
 * @param vehicleOptions список опций выбора техники.
 * @param placesOptions список опций пунктов погрузки и разгрузки.
 */
export const getBaseColumns = (
  vehicleOptions: SelectOption[],
  placesOptions: {
    readonly load: SelectOption[];
    readonly unload: SelectOption[];
  },
): ColumnDef<EnrichedTrip>[] => [
  {
    header: 'Наименование техники',
    accessorKey: 'vehicle_id',
    accessorFn: (row) => row.vehicle_name,
    size: 190,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: vehicleOptions,
      valueType: 'number',
      readOnlyEdit: true,
    },
  },
  {
    header: 'Номер рейса/ковша',
    accessorKey: 'cycle_num',
    size: 155,
    meta: {
      dataType: ColumnDataTypes.NUMBER,
      required: false,
      hideOnCreate: true,
      readOnly: true,
    },
  },
  {
    header: 'Время начала рейса',
    accessorKey: 'cycle_started_at',
    size: 130,
    meta: {
      dataType: ColumnDataTypes.DATETIME,
      columnWithMaxValue: 'cycle_completed_at',
      validation: DATE_VALIDATION,
      crossValidate: validateDateRange({
        max: { field: 'cycle_completed_at', message: 'Время начала рейса не может быть позже окончания цикла.' },
      }),
    },
  },
  {
    header: 'Время окончания цикла',
    accessorKey: 'cycle_completed_at',
    size: 170,
    meta: {
      dataType: ColumnDataTypes.DATETIME,
      columnWithMinValue: 'cycle_started_at',
      validation: DATE_VALIDATION,
      crossValidate: validateDateRange({
        min: { field: 'cycle_started_at', message: 'Время окончания не может быть раньше начала рейса' },
      }),
    },
  },
  {
    header: 'Пункт погрузки',
    accessorKey: 'loading_place_id',
    accessorFn: (row) => row.loading_place_name,
    size: 130,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: placesOptions.load,
      valueType: 'number',
    },
  },
  {
    header: 'Время начала погрузки',
    accessorKey: 'loading_timestamp',
    size: 130,
    meta: {
      dataType: ColumnDataTypes.DATETIME,
      columnWithMinValue: 'cycle_started_at',
      columnWithMaxValue: 'cycle_completed_at',
      validation: DATE_VALIDATION,
      crossValidate: validateDateRange({
        min: { field: 'cycle_started_at', message: 'Время погрузки не может быть раньше начала рейса' },
        max: { field: 'unloading_timestamp', message: 'Время погрузки не может быть позже начала разгрузки' },
      }),
      required: false,
      hideOnCreate: true,
    },
  },
  {
    header: 'Пункт разгрузки',
    accessorKey: 'unloading_place_id',
    accessorFn: (row) => row.unloading_place_name,
    size: 170,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: placesOptions.unload,
      valueType: 'number',
    },
  },
  {
    header: 'Время начала разгрузки',
    accessorKey: 'unloading_timestamp',
    size: 170,
    meta: {
      dataType: ColumnDataTypes.DATETIME,
      columnWithMinValue: 'cycle_started_at',
      columnWithMaxValue: 'cycle_completed_at',
      validation: DATE_VALIDATION,
      crossValidate: validateDateRange({
        min: { field: 'loading_timestamp', message: 'Время разгрузки не может быть раньше погрузки' },
      }),
      required: false,
      hideOnCreate: true,
    },
  },
  {
    header: 'Тип рейса',
    accessorKey: 'trip_type',
    accessorFn: (row) => {
      if (!hasValue(row.trip_type)) return 'не указан';
      return row.trip_type === 'unplanned' ? 'внеплановый' : 'запланированный';
    },
    size: 120,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: [
        { value: 'unplanned', label: 'внеплановый' },
        { value: 'planned', label: 'запланированный' },
      ],
      required: false,
      hideOnCreate: true,
      readOnly: true,
      valueType: 'string',
    },
  },
  {
    header: 'Источник',
    accessorKey: 'source',
    accessorFn: (row) => (row.source === 'system' ? 'система' : 'диспетчер'),
    size: 170,
    meta: {
      dataType: ColumnDataTypes.SELECT,
      options: [
        { value: 'system', label: 'система' },
        { value: 'dispatcher', label: 'диспетчер' },
      ],
      required: false,
      hideOnCreate: true,
      readOnly: true,
      valueType: 'string',
    },
  },
  {
    header: 'Объем, м³',
    accessorKey: 'change_amount',
    size: 165,
    meta: {
      dataType: ColumnDataTypes.NUMBER,
      required: false,
      validation: POSITIVE_NUMBER_VALIDATION,
    },
  },
];

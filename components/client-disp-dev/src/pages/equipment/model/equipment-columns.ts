import { getVehicleTypeDisplayName, vehicleTypeOptions } from '@/entities/vehicle';

import type { EquipmentModel } from '@/shared/api/endpoints/equipment-models';
import type { Vehicle } from '@/shared/api/endpoints/vehicles';
import { POSITIVE_NUMBER_VALIDATION } from '@/shared/lib/validation';
import { ColumnDataTypes, type ColumnDef, type EditableSelectHandlers } from '@/shared/ui/Table';

/** Опции для настройки колонок таблицы оборудования. */
interface ColumnsOptions {
  /** Список моделей оборудования для выпадающего списка. */
  equipmentModels: readonly EquipmentModel[];
  /** Обработчики событий для редактируемого поля выбора модели. */
  modelHandlers: Readonly<EditableSelectHandlers>;
}

/** Создает базовую конфигурацию колонок для таблицы оборудования. */
export const getBaseColumns = (options: ColumnsOptions) =>
  [
    {
      header: 'Гаражный номер',
      accessorKey: 'registration_number',
      accessorFn: (row) => row.registration_number,
      size: 150,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Тип',
      accessorKey: 'vehicle_type',
      accessorFn: (row) => getVehicleTypeDisplayName(row.vehicle_type),
      size: 100,
      meta: {
        dataType: ColumnDataTypes.SELECT,
        options: vehicleTypeOptions,
        valueType: 'string',
      },
    },
    {
      header: 'Модель',
      accessorKey: 'model_id',
      accessorFn: (row) => row.model?.name ?? '',
      size: 150,
      meta: {
        dataType: ColumnDataTypes.EDITABLE_SELECT,
        options: options.equipmentModels.map((model) => ({
          value: String(model.id),
          label: model.name,
        })),
        valueType: 'number',
        handlers: options.modelHandlers,
        autoFill: Object.fromEntries(
          options.equipmentModels.map((model) => [
            String(model.id),
            {
              volume_m3: model.volume_m3,
              load_capacity_tons: model.load_capacity_tons,
              max_speed: model.max_speed,
              tank_volume: model.tank_volume,
            },
          ]),
        ),
      },
    },
    {
      header: 'Идентификатор/номер',
      accessorKey: 'serial_number',
      size: 175,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'Объем кузова/ковша, м³',
      accessorKey: 'volume_m3',
      accessorFn: (row) => row.model?.volume_m3,
      size: 185,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: POSITIVE_NUMBER_VALIDATION,
      },
    },
    {
      header: 'Грузоподъемность, т.',
      accessorKey: 'load_capacity_tons',
      accessorFn: (row) => row.model?.load_capacity_tons,
      size: 165,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: POSITIVE_NUMBER_VALIDATION,
      },
    },
    {
      header: 'Макс. скорость, км/ч',
      accessorKey: 'max_speed',
      accessorFn: (row) => row.model?.max_speed,
      size: 160,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: POSITIVE_NUMBER_VALIDATION,
      },
    },
    {
      header: 'Объём бака, л.',
      accessorKey: 'tank_volume',
      accessorFn: (row) => row.model?.tank_volume,
      size: 125,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        validation: POSITIVE_NUMBER_VALIDATION,
      },
    },
    {
      header: 'Дата ввода в эксплуатацию',
      accessorKey: 'active_from',
      size: 205,
      meta: {
        required: false,
        dataType: ColumnDataTypes.DATE,
        columnWithMaxValue: 'active_to',
      },
    },
    {
      header: 'Дата вывода из эксплуатации',
      accessorKey: 'active_to',
      size: 220,
      meta: {
        required: false,
        dataType: ColumnDataTypes.DATE,
        columnWithMinValue: 'active_from',
      },
    },
  ] as const satisfies ColumnDef<Vehicle>[];

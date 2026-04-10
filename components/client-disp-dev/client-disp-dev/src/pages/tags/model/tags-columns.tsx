import type { Place } from '@/shared/api/endpoints/places';
import { type Tag, placeTypeLabels } from '@/shared/api/endpoints/tags';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { MAC_ADDRESS_VALIDATION } from '@/shared/lib/validation';
import { EMPTY_COORDINATES, type LocationModel, normalizeLocation } from '@/shared/models/LocationModel';
import { ColumnDataTypes, type ColumnDef } from '@/shared/ui/Table';

/**
 * Плоская структура данных метки для таблицы меток.
 * Поля из вложенного объекта `place` развёрнуты на верхний уровень.
 */
export type TagTableData = Omit<Tag, 'place' | 'radius'> & {
  /** Название места, к которому привязана метка. */
  readonly place_name: string;
  /** Координаты места (широта/долгота) или пустые координаты. */
  readonly location: LocationModel | typeof EMPTY_COORDINATES;
  /** Локализованный тип места или `null`, если не указан. */
  readonly tag_type: string | null;
};

/**
 * Преобразует Tag в плоскую структуру для таблицы.
 * Выносит вложенные поля из `place` на верхний уровень и нормализует данные.
 *
 * @param tag Исходная метка с вложенной структурой `place`.
 * @returns Плоская структура данных для отображения в таблице.
 */
export function transformTagToTableData(tag: Tag): TagTableData {
  const placeName = hasValueNotEmpty(tag.place?.name) ? tag.place.name : '';
  const location = normalizeLocation(tag.place?.location);
  const tagType = tag.place?.type ? placeTypeLabels[tag.place.type] : null;

  return {
    id: tag.id,
    tag_name: tag.tag_name,
    tag_mac: tag.tag_mac,
    place_id: tag.place_id,
    battery_level: tag.battery_level,
    battery_updated_at: tag.battery_updated_at,
    x: tag.x,
    y: tag.y,
    z: tag.z,
    horizon_id: tag.horizon_id,
    name: tag.name,
    point_type: tag.point_type,
    point_id: tag.point_id,
    beacon_id: tag.beacon_id,
    beacon_mac: tag.beacon_mac,
    beacon_place: tag.beacon_place,
    place_name: placeName,
    location,
    tag_type: tagType,
  };
}

/**
 * Возвращает колонки для таблицы меток.
 *
 * @param places все доступные места.
 */
export function tagsColumns(places: readonly Place[]) {
  return [
    {
      header: 'ID-метки',
      accessorKey: 'tag_name',
      size: 200,
      meta: {
        dataType: ColumnDataTypes.TEXT,
      },
    },
    {
      header: 'MAC-адрес',
      accessorKey: 'tag_mac',
      size: 180,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        validation: MAC_ADDRESS_VALIDATION,
        mask: 'mac-address',
      },
    },
    {
      header: 'Место установки',
      accessorKey: 'place_id',
      accessorFn: (row) => row.place_name,
      size: 200,
      meta: {
        dataType: ColumnDataTypes.SELECT,
        options: places.map((place) => ({
          label: place.name,
          value: String(place.id),
        })),
        valueType: 'number',
        required: false,
        autoFill: Object.fromEntries(
          places.map((place) => [
            String(place.id),
            {
              location: normalizeLocation(place.location),
              tag_type: placeTypeLabels[place.type],
            },
          ]),
        ),
      },
    },
    {
      header: 'Координаты',
      accessorKey: 'location',
      accessorFn: (row) => {
        return hasValueNotEmpty(row.location.lat) && hasValueNotEmpty(row.location.lon)
          ? `${row.location.lat}, ${row.location.lon}`
          : null;
      },
      size: 130,
      meta: {
        dataType: ColumnDataTypes.COORDINATES,
        required: false,
        readOnly: true,
      },
    },
    {
      header: 'Тип метки',
      accessorKey: 'tag_type',
      size: 130,
      meta: {
        dataType: ColumnDataTypes.TEXT,
        required: false,
        readOnly: true,
      },
    },
    {
      header: 'Уровень заряда, %',
      accessorKey: 'battery_level',
      size: 150,
      meta: {
        dataType: ColumnDataTypes.NUMBER,
        hideOnCreate: true,
        readOnly: true,
        required: false,
      },
    },
    {
      header: 'Дата изменения',
      accessorKey: 'battery_updated_at',
      size: 150,
      meta: {
        dataType: ColumnDataTypes.DATE,
        hideOnCreate: true,
        readOnly: true,
        required: false,
      },
    },
  ] as const satisfies ColumnDef<TagTableData>[];
}

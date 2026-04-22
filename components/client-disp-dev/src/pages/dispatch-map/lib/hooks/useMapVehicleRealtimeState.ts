import type { Vector3Tuple } from 'three';

import { DEFAULT_VEHICLE_TYPE } from '@/entities/vehicle';

import { type Place, useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import {
  useGetAllVehiclesQuery,
  useGetVehicleCoordinatesStreamQuery,
  useGetVehiclePlacesQuery,
  useGetVehiclesStreamQuery,
  useGetVehicleStateQuery,
  type VehicleCoordinates,
  type VehiclePlaceItem,
  type VehicleStateEvent,
  type VehicleStateItem,
  type VehicleType,
} from '@/shared/api/endpoints/vehicles';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import type { ElementCoordinates } from '@/shared/ui/types';

import { toScene } from '../coordinates';

/** Общее состояние одной машины на карте: координаты, местоположение и статус. */
export interface VehicleMapStateItem {
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Название транспортного средства. */
  readonly name: string;
  /** Тип транспортного средства. */
  readonly vehicleType: VehicleType;
  /** Системное имя статуса из справочника. */
  readonly statusSystemName: string | null;
  /** Горизонт на котором находится машина. */
  readonly horizon_id: number | null;
  /** Место, где находится машина. */
  readonly place_id: number | null;
  /** Позиция в координатах 3D-сцены (y = 0). `null` — координаты неизвестны. */
  readonly scenePosition: Vector3Tuple | null;
}

/** Машина, видимая на 3D-сцене: `scenePosition` гарантированно не `null`. */
export type VisibleVehicle = Omit<VehicleMapStateItem, 'scenePosition'> & {
  readonly scenePosition: Vector3Tuple;
};

/** Промежуточное представление машины до добавления доп. данных. */
interface RawVehicleState {
  /** Идентификатор транспортного средства. */
  readonly vehicle_id: number;
  /** Системное имя статуса (из REST или SSE). */
  readonly statusSystemName: string | null;
  /** Горизонт, на котором находится машина. */
  readonly horizon_id: number | null;
  /** Идентификатор места, где находится машина. */
  readonly place_id: number | null;
  /** Позиция в координатах 3D-сцены (y = 0). `null` — координаты ещё не получены. */
  readonly scenePosition: Vector3Tuple | null;
}

const EMPTY_SSE_STREAM = {} as const satisfies Record<number, VehicleStateEvent>;
const EMPTY_WS_STREAM = {} as const satisfies Record<number, VehicleCoordinates>;

/**
 * Собирает данные о положении и статусе машин.
 *
 * Агрегирует пять источников в единый источник данных:
 * 1. REST `/vehicles` — `name`, `vehicle_type`.
 * 2. REST `/vehicles/places` — `place_id`, `horizon_id`.
 * 3. REST `/vehicles/state` — `status` → `statusSystemName`.
 * 4. SSE `/events/stream/vehicles` — обновляет `statusSystemName`, `horizon_id`, `place_id`.
 * 5. WS `/ws/vehicle-tracking` — обновляет координаты → `scenePosition`.
 */
export function useMapVehicleRealtimeState() {
  const { data: vehiclePlacesData, isLoading: isPlacesLoading } = useGetVehiclePlacesQuery();
  const { data: vehicleStatusData, isLoading: isStatusLoading } = useGetVehicleStateQuery();
  const { data: sseStream } = useGetVehiclesStreamQuery();
  const { data: wsStream } = useGetVehicleCoordinatesStreamQuery();
  const { data: allPlacesData, isLoading: isAllPlacesLoading } = useGetAllPlacesQuery();
  const { data: allVehicles, isLoading: isVehiclesLoading } = useGetAllVehiclesQuery();

  const isLoading = isPlacesLoading || isStatusLoading || isAllPlacesLoading || isVehiclesLoading;

  const placesMap = buildPlacesCoordinateMap(allPlacesData?.items ?? EMPTY_ARRAY);

  const initialMap = buildInitialMap(vehiclePlacesData?.items ?? EMPTY_ARRAY, vehicleStatusData?.items ?? EMPTY_ARRAY);
  const withSse = applySSEOverlay(initialMap, sseStream ?? EMPTY_SSE_STREAM);
  const withWs = applyCoordinatesOverlay(withSse, wsStream ?? EMPTY_WS_STREAM);
  const withFallback = applyPlaceCoordinateFallback(withWs, placesMap);
  const data = applyVehicleEntityOverlay(withFallback, allVehicles?.entities);

  return { data, isLoading };
}

/**
 * Собирает начальные данные: места/горизонты и статус.
 */
function buildInitialMap(places: readonly VehiclePlaceItem[], states: readonly VehicleStateItem[]) {
  const map: Record<number, RawVehicleState> = {};

  for (const place of places) {
    map[place.vehicle_id] = {
      vehicle_id: place.vehicle_id,
      statusSystemName: null,
      horizon_id: place.horizon_id,
      place_id: place.place_id,
      scenePosition: null,
    };
  }

  for (const stateItem of states) {
    const existing = map[stateItem.vehicle_id];
    if (existing) {
      map[stateItem.vehicle_id] = { ...existing, statusSystemName: stateItem.status };
    } else {
      map[stateItem.vehicle_id] = {
        vehicle_id: stateItem.vehicle_id,
        statusSystemName: stateItem.status,
        horizon_id: null,
        place_id: null,
        scenePosition: null,
      };
    }
  }

  return map;
}

/**
 * Добавляет реалтайм данные: горизонт, место, статус к начальному состоянию.
 */
function applySSEOverlay(initial: Record<number, RawVehicleState>, stream: Record<number, VehicleStateEvent>) {
  const keys = Object.keys(stream);
  if (keys.length === 0) return initial;

  const result = { ...initial };

  for (const key of keys) {
    const event = stream[Number(key)];
    const existing = result[event.vehicle_id];
    result[event.vehicle_id] = {
      vehicle_id: event.vehicle_id,
      statusSystemName: event.state,
      horizon_id: event.horizon_id,
      place_id: event.place_id,
      scenePosition: existing?.scenePosition ?? null,
    };
  }

  return result;
}

/**
 * Добавляет координаты из WebSocket, сразу преобразуя в координаты 3D-сцены.
 */
function applyCoordinatesOverlay(
  state: Record<number, RawVehicleState>,
  vehicleCoordinates: Record<number, VehicleCoordinates>,
) {
  const keys = Object.keys(vehicleCoordinates);
  if (keys.length === 0) return state;

  const result = { ...state };

  for (const key of keys) {
    const coordinates = vehicleCoordinates[Number(key)];
    const existing = result[coordinates.vehicle_id];

    result[coordinates.vehicle_id] = {
      vehicle_id: coordinates.vehicle_id,
      statusSystemName: existing?.statusSystemName ?? null,
      horizon_id: existing?.horizon_id ?? null,
      place_id: existing?.place_id ?? null,
      scenePosition: toScene(coordinates.lon, coordinates.lat),
    };
  }

  return result;
}

/**
 * Строит карту координат мест для быстрого поиска по id.
 */
function buildPlacesCoordinateMap(places: readonly Place[]) {
  const map = new Map<number, ElementCoordinates>();

  for (const place of places) {
    if (hasValue(place.x) && hasValue(place.y)) {
      map.set(place.id, { x: place.x, y: place.y });
    }
  }

  return map;
}

/**
 * Подставляет координаты места для машин без lat|lon данных.
 * Координаты из WS приоритетнее, фоллбек срабатывает только при отсутствии scenePosition.
 */
function applyPlaceCoordinateFallback(
  state: Record<number, RawVehicleState>,
  placesMap: Map<number, ElementCoordinates>,
) {
  let result = state;
  let hasChanges = false;

  for (const key in state) {
    const item = state[key];
    if (item.scenePosition !== null) continue;
    if (item.place_id === null) continue;

    const place = placesMap.get(item.place_id);
    if (!place) continue;

    if (!hasChanges) {
      result = { ...state };
      hasChanges = true;
    }
    result[item.vehicle_id] = { ...item, scenePosition: toScene(place.x, place.y) };
  }

  return result;
}

/**
 * Добавляет к промежуточному состоянию машины данные из справочника машин (название, тип).
 */
function applyVehicleEntityOverlay(
  state: Record<number, RawVehicleState>,
  entities?: Record<number, { name: string; vehicle_type: VehicleType }>,
) {
  const result: Record<number, VehicleMapStateItem> = {};

  for (const key in state) {
    const item = state[key];
    const vehicle = entities?.[item.vehicle_id];

    result[item.vehicle_id] = {
      ...item,
      name: vehicle?.name ?? `№${item.vehicle_id}`,
      vehicleType: vehicle?.vehicle_type ?? DEFAULT_VEHICLE_TYPE,
    };
  }

  return result;
}

/**
 * Проверяет, что машина должна быть видна на карте для заданного горизонта.
 */
export function isVisibleOnMap(
  vehicle: VehicleMapStateItem,
  horizonId: number | null,
  hiddenIds: readonly number[],
): vehicle is VisibleVehicle {
  if (hiddenIds.includes(vehicle.vehicle_id)) return false;

  if (vehicle.horizon_id !== horizonId || vehicle.place_id === null) return false;

  return hasValue(vehicle.scenePosition);
}

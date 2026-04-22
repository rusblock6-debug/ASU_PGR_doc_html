import { skipToken } from '@reduxjs/toolkit/query';
import type { Vector3Tuple } from 'three';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import type { MapPlayerPlaybackItem } from '@/shared/api/endpoints/map-player';
import { useGetAllVehiclesQuery, type VehicleType } from '@/shared/api/endpoints/vehicles';
import type { NormalizedVehiclesResponse } from '@/shared/api/endpoints/vehicles';
import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { toScene } from '../../../lib/coordinates';
import { useMapVehicleHistoryState } from '../../../lib/hooks/useMapVehicleHistoryState';
import { tooltipStore } from '../../../lib/tooltip-store';
import {
  selectMapFocusTarget,
  selectMapMode,
  selectSelectedHorizonId,
  selectVehicleHistoryMarks,
} from '../../../model/selectors';
import { Mode } from '../../../model/types';
import { EventMarker } from '../EventMarker';
import { VehicleMarker } from '../VehicleMarker';

import { VehicleTooltip } from './VehicleTooltip';

/** Представляет историческую запись о состоянии оборудования. */
interface HistoryVehicle {
  /** Возвращает момент времени. */
  readonly timestamp: string;
  /** Возвращает координаты. */
  readonly position: Vector3Tuple;
  /** Возвращает наименование. */
  readonly name: string;
  /** Возвращает тип. */
  readonly vehicleType: VehicleType;
  /** Возвращает идентификатор. */
  readonly vehicleId: number;
  /** Возвращает скорость. */
  readonly speed: number | null;
  /** Возвращает остаток топлива. */
  readonly fuel: number | null;
  /** Возвращает объем топливного бака. */
  readonly tankVolume: number | null;
}

/**
 * Слой транспортных средств на 3D-карте.
 *
 * Отображает маркеры машин с фильтрацией скрытых и нулевых координат,
 * а также тултип при наведении.
 */
export function HistoryVehiclesLayer() {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const mapMode = useAppSelector(selectMapMode);
  const vehicleHistoryMarks = useAppSelector(selectVehicleHistoryMarks);

  const { data: graphData } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const { data: allVehicles } = useGetAllVehiclesQuery();

  const { data } = useMapVehicleHistoryState();

  const isHistoryMode = mapMode === Mode.HISTORY;

  if (!graphData || !isHistoryMode) return null;

  const vehicleList = mapMapPlayerPlaybackItemToHistoryVehicle(MAP_SCENE.VEHICLES_Y, data, allVehicles);

  const handleVehicleHover = (vehicleId: number | null) => {
    if (vehicleId === null) {
      tooltipStore.hide();
      return;
    }

    const vehicle = vehicleList.find((vehicle) => vehicle.vehicleId === vehicleId);
    if (!vehicle) return;

    tooltipStore.show(
      <VehicleTooltip
        id={vehicle.vehicleId}
        name={vehicle.name}
        timestamp={vehicle.timestamp}
        speed={vehicle.speed}
        fuel={vehicle.fuel}
        tankVolume={vehicle.tankVolume}
      />,
    );
  };

  const vehicleMarksList = mapMapPlayerPlaybackItemToHistoryVehicle(
    MAP_SCENE.VEHICLE_MARKS_Y,
    vehicleHistoryMarks,
    allVehicles,
  );

  const handleVehicleMarkHover = (vehicleId: number | null, timestamp: string | null) => {
    if (!hasValue(vehicleId) || !hasValue(timestamp)) {
      tooltipStore.hide();
      return;
    }

    const vehicle = vehicleMarksList.find(
      (vehicle) => vehicle.vehicleId === vehicleId && vehicle.timestamp === timestamp,
    );
    if (!vehicle) return;

    tooltipStore.show(
      <VehicleTooltip
        id={vehicle.vehicleId}
        name={vehicle.name}
        timestamp={vehicle.timestamp}
        speed={vehicle.speed}
        fuel={vehicle.fuel}
        tankVolume={vehicle.tankVolume}
      />,
    );
  };

  return (
    <>
      <group>
        {vehicleList.map((vehicle) => (
          <VehicleMarker
            key={vehicle.vehicleId}
            id={vehicle.vehicleId}
            vehicleType={vehicle.vehicleType}
            name={vehicle.name}
            position={vehicle.position}
            isSelected={focusTarget?.entity === 'vehicle' && focusTarget.id === vehicle.vehicleId}
            color="var(--base-orange)"
            onHover={handleVehicleHover}
          />
        ))}
      </group>
      <group>
        {vehicleMarksList.map((vehicle) => (
          <EventMarker
            key={`${vehicle.vehicleId}-${vehicle.timestamp}`}
            id={vehicle.vehicleId}
            timestamp={vehicle.timestamp}
            position={vehicle.position}
            isSelected={focusTarget?.entity === 'vehicle' && focusTarget.id === vehicle.vehicleId}
            onHover={handleVehicleMarkHover}
          />
        ))}
      </group>
    </>
  );
}

/**
 * Преобразует список элементов истории получаемый с сервера в список данных для отображения.
 *
 * @param yCoordinate значение координаты Y.
 * @param items список элементов истории, полученный от сервера.
 * @param allVehicles список оборудования.
 */
function mapMapPlayerPlaybackItemToHistoryVehicle(
  yCoordinate: number,
  items?: readonly MapPlayerPlaybackItem[],
  allVehicles?: NormalizedVehiclesResponse,
) {
  return (
    items
      ?.map<HistoryVehicle | undefined>((item) => {
        const vehicleInfo = allVehicles?.entities[item.vehicle_id];
        const sceneCoordinates = toScene(item.lon, item.lat, yCoordinate);

        if (vehicleInfo) {
          return {
            timestamp: item.timestamp,
            position: sceneCoordinates,
            name: vehicleInfo.name,
            vehicleType: vehicleInfo.vehicle_type,
            vehicleId: item.vehicle_id,
            speed: item.speed,
            fuel: item.fuel,
            tankVolume: vehicleInfo.model?.tank_volume ?? null,
          };
        }
      })
      .filter(hasValue) ?? []
  );
}

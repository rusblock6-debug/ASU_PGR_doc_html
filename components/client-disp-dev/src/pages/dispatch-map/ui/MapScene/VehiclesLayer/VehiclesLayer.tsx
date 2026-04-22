import { skipToken } from '@reduxjs/toolkit/query';
import type { MouseEvent } from 'react';
import type { Vector3Tuple } from 'three';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { isVisibleOnMap, useMapVehicleRealtimeState } from '../../../lib/hooks/useMapVehicleRealtimeState';
import { tooltipStore } from '../../../lib/tooltip-store';
import {
  selectHiddenVehicleIds,
  selectMapFocusTarget,
  selectMapMode,
  selectSelectedHorizonId,
} from '../../../model/selectors';
import { mapActions } from '../../../model/slice';
import { Mode } from '../../../model/types';
import { VehicleMarker } from '../VehicleMarker';

import { VehicleTooltip } from './VehicleTooltip';

/**
 * Слой транспортных средств на 3D-карте.
 *
 * Отображает маркеры машин с фильтрацией скрытых и нулевых координат,
 * а также тултип при наведении.
 */
export function VehiclesLayer({ interactive = true }: Readonly<{ interactive?: boolean }>) {
  const dispatch = useAppDispatch();
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data: graphData } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const hiddenVehicleIds = useAppSelector(selectHiddenVehicleIds);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const mapMode = useAppSelector(selectMapMode);

  const isHistoryMode = mapMode === Mode.HISTORY;

  const { data: statusesData } = useGetAllStatusesQuery();

  const { data: realtimeState } = useMapVehicleRealtimeState();

  if (!graphData || isHistoryMode) return null;

  const statusBySystemName = new Map(statusesData?.items.map((status) => [status.system_name, status]));

  const vehicleList = Object.values(realtimeState)
    .filter((vehicle) => isVisibleOnMap(vehicle, horizonId, hiddenVehicleIds))
    .map((vehicle) => ({
      ...vehicle,
      position: [vehicle.scenePosition[0], MAP_SCENE.VEHICLES_Y, vehicle.scenePosition[2]] as Vector3Tuple,
    }));

  const handleVehicleHover = (vehicleId: number | null) => {
    if (vehicleId === null) {
      tooltipStore.hide();
      return;
    }

    const vehicle = vehicleList.find((vehicle) => vehicle.vehicle_id === vehicleId);
    if (!vehicle) return;

    tooltipStore.show(
      <VehicleTooltip
        vehicleId={vehicle.vehicle_id}
        vehicleName={vehicle.name}
      />,
    );
  };

  const handleVehicleContextMenu = (vehicleId: number, event: MouseEvent) => {
    tooltipStore.hide();

    const vehicle = vehicleList.find((vehicle) => vehicle.vehicle_id === vehicleId);
    if (!vehicle) return;

    dispatch(
      mapActions.setVehicleContextMenu({
        vehicleId: vehicle.vehicle_id,
        clickPosition: { x: event.clientX, y: event.clientY },
      }),
    );
  };

  return (
    <group>
      {vehicleList.map((vehicle) => (
        <VehicleMarker
          key={vehicle.vehicle_id}
          id={vehicle.vehicle_id}
          vehicleType={vehicle.vehicleType}
          name={vehicle.name}
          position={vehicle.position}
          isSelected={focusTarget?.entity === 'vehicle' && focusTarget.id === vehicle.vehicle_id}
          color={
            hasValueNotEmpty(vehicle.statusSystemName)
              ? statusBySystemName.get(vehicle.statusSystemName)?.color
              : undefined
          }
          interactive={interactive}
          onHover={handleVehicleHover}
          onContextMenu={handleVehicleContextMenu}
        />
      ))}
    </group>
  );
}

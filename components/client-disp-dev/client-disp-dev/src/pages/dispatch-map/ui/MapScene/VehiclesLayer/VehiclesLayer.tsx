import { skipToken } from '@reduxjs/toolkit/query';

import { useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllStatusesQuery } from '@/shared/api/endpoints/statuses/statuses-rtk';
import { hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { MAP_SCENE } from '../../../config/map-scene';
import { toScene } from '../../../lib/coordinates';
import { tooltipStore } from '../../../lib/tooltip-store';
import { selectHiddenVehicleIds, selectMapFocusTarget, selectSelectedHorizonId } from '../../../model/selectors';

import { VehicleMarker } from './VehicleMarker';
import { VehicleTooltip } from './VehicleTooltip';

/**
 * Данные о транспортном средстве, получаемые по WebSocket.
 */
export interface VehicleData {
  /** ID транспорта. */
  vehicle_id: number;
  /** Название транспорта. */
  name?: string;
  /** Широта. */
  lat: number;
  /** Долгота. */
  lon: number;
  /** Текущее состояние. */
  state?: string;
  /** Текущая скорость, км/ч. */
  speed?: number | null;
  /** Ближайшая точка привязки. */
  tag?: { point_name: string; point_type: string } | null;
}

/**
 * Слой транспортных средств на 3D-карте.
 *
 * Отображает маркеры машин с фильтрацией скрытых и нулевых координат,
 * а также тултип при наведении.
 */
export function VehiclesLayer({
  vehicles,
  interactive = true,
}: Readonly<{
  vehicles: Record<string, VehicleData>;
  interactive?: boolean;
}>) {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { data } = useGetHorizonGraphQuery(horizonId ?? skipToken);
  const hiddenVehicleIds = useAppSelector(selectHiddenVehicleIds);
  const focusTarget = useAppSelector(selectMapFocusTarget);
  const { data: statusesData } = useGetAllStatusesQuery();

  if (!data) return null;

  const statusBySystemName = new Map(statusesData?.items.map((status) => [status.system_name, status]));

  const vehicleList = Object.values(vehicles).filter(
    (value) => value.lat !== 0 && value.lon !== 0 && !hiddenVehicleIds.includes(value.vehicle_id),
  );

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
        vehicleName={vehicle.name ?? `№${vehicle.vehicle_id}`}
      />,
    );
  };

  return (
    <group>
      {vehicleList.map((vehicle) => (
        <VehicleMarker
          key={vehicle.vehicle_id}
          id={vehicle.vehicle_id}
          // добавить определение какой тип у машины, сейчас хардкод type="shas"
          vehicleType="shas"
          name={vehicle.name ?? `#${vehicle.vehicle_id}`}
          position={toScene(vehicle.lon, vehicle.lat, MAP_SCENE.VEHICLES_Y)}
          isSelected={focusTarget?.entity === 'vehicle' && focusTarget.id === vehicle.vehicle_id}
          color={hasValueNotEmpty(vehicle.state) ? statusBySystemName.get(vehicle.state)?.color : undefined}
          interactive={interactive}
          onHover={handleVehicleHover}
        />
      ))}
    </group>
  );
}

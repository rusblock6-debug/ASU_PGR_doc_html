import { type ChangeEvent, useState } from 'react';

import { type AssignPlaceType } from '@/shared/api/endpoints/fleet-control';
import DockCloseIcon from '@/shared/assets/icons/ic-dock-close.svg?react';
import ParkIcon from '@/shared/assets/icons/ic-park-orange.svg?react';
import { TextInput } from '@/shared/ui/TextInput';

import { useAssignmentVehicle } from '../../../../lib/hooks/useAssignmentVehicle';
import { useFleetControlPageDataSource } from '../../../../lib/hooks/useFleetControlPageDataSource';
import { Divider } from '../../../Divider';

import styles from './MoveIn.module.css';

/**
 * Представляет свойства компонента элемента контента контекстного меню для перемещения техники.
 */
interface MoveInProps {
  /** Возвращает идентификатор оборудования. */
  readonly vehicleId: number;
  /** Возвращает идентификатор оборудования. */
  readonly vehicleName: string;
  /** Возвращает тип текущего назначенного места. */
  readonly currentAssignedPlace: AssignPlaceType;
  /** Возвращает идентификатор текущего гаража. */
  readonly currentGarageId?: number | null;
  /** Возвращает идентификатор текущего места погрузки. */
  readonly currentRoutePlaceAId?: number | null;
  /** Возвращает идентификатор текущего места разгрузки. */
  readonly currentRoutePlaceBId?: number | null;
  /** Возвращает делегат, вызываемый при закрытии контекстного меню. */
  readonly onClose: () => void;
}

/**
 * Представляет компонент элемента контента контекстного меню для перемещения техники.
 */
export function MoveIn({
  vehicleId,
  vehicleName,
  currentAssignedPlace,
  currentGarageId = null,
  currentRoutePlaceAId = null,
  currentRoutePlaceBId = null,
  onClose,
}: MoveInProps) {
  const { fleetControlData, places } = useFleetControlPageDataSource();

  const garages = fleetControlData?.garages;

  const routes = fleetControlData?.routes;

  const [searchRouteValue, setSearchRouteValue] = useState('');

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSearchRouteValue(event.target.value);
  };

  const onInputClear = () => {
    setSearchRouteValue('');
  };

  const visibleRoutes =
    routes?.filter((route) => {
      if (route.place_a_id === currentRoutePlaceAId && route.place_b_id === currentRoutePlaceBId) {
        return false;
      }

      const placeAName = places.find((place) => place.id === route.place_a_id);
      const placeBName = places.find((place) => place.id === route.place_b_id);

      return (
        placeAName?.name.trim().toLowerCase().includes(searchRouteValue.trim().toLowerCase()) ||
        placeBName?.name.trim().toLowerCase().includes(searchRouteValue.trim().toLowerCase())
      );
    }) ?? [];

  const visibleGarages = garages?.filter((garage) => garage.id !== currentGarageId) ?? [];

  const handleAssignment = useAssignmentVehicle({ onClose });

  return (
    <div className={styles.root}>
      {currentAssignedPlace === 'ROUTE' && (
        <>
          <div
            className={styles.menu_item}
            onClick={() =>
              handleAssignment({
                targetKind: 'NO_TASK',
                vehicleId,
                vehicleName,
                currentAssignedPlace,
                currentGarageId,
                currentRoutePlaceAId,
                currentRoutePlaceBId,
              })
            }
          >
            <DockCloseIcon className={styles.grey_icon} />
            <p className={styles.label}>Нет задания</p>
          </div>
          <Divider
            height={1}
            color="var(--bg-widget-hover)"
          />
        </>
      )}
      {visibleGarages.length > 0 && (
        <>
          {visibleGarages.map((garage) => (
            <div
              key={garage.id}
              className={styles.menu_item}
              onClick={() =>
                handleAssignment({
                  targetKind: 'GARAGE',
                  targetGarageId: garage.id,
                  vehicleId,
                  vehicleName,
                  currentAssignedPlace,
                  currentGarageId,
                  currentRoutePlaceAId,
                  currentRoutePlaceBId,
                })
              }
            >
              <ParkIcon className={styles.grey_icon} />
              <p className={styles.label}>{garage.name}</p>
            </div>
          ))}
          <Divider
            height={1}
            color="var(--bg-widget-hover)"
          />
        </>
      )}
      <TextInput
        placeholder="Поиск"
        variant="outline"
        clearable
        className={styles.input}
        value={searchRouteValue}
        onChange={onInputChange}
        onClear={onInputClear}
      />
      {visibleRoutes.length > 0 ? (
        visibleRoutes.map((route) => (
          <div
            key={route.route_id}
            className={styles.menu_item}
            onClick={() =>
              handleAssignment({
                targetKind: 'ROUTE',
                targetRoutePlaceAId: route.place_a_id,
                targetRoutePlaceBId: route.place_b_id,
                vehicleId,
                vehicleName,
                currentAssignedPlace,
                currentGarageId,
                currentRoutePlaceAId,
                currentRoutePlaceBId,
              })
            }
          >
            <p className={styles.label}>
              {places.find((place) => place.id === route.place_a_id)?.name}
              {' — '}
              {places.find((place) => place.id === route.place_b_id)?.name}
            </p>
          </div>
        ))
      ) : (
        <div className={styles.no_data}>Нет доступных маршрутов</div>
      )}
    </div>
  );
}

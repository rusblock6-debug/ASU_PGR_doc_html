import { type ChangeEvent, useState } from 'react';

import { type AssignPlaceType, useAssignmentVehicleMutation } from '@/shared/api/endpoints/fleet-control';
import DockCloseIcon from '@/shared/assets/icons/ic-dock-close.svg?react';
import ParkIcon from '@/shared/assets/icons/ic-park-orange.svg?react';
import { useConfirm } from '@/shared/lib/confirm';
import { TextInput } from '@/shared/ui/TextInput';
import { toast } from '@/shared/ui/Toast';

import { useFleetControlPageDataSource } from '../../../../lib/hooks/useFleetControlPageDataSource';
import { useFleetControlPageContext } from '../../../../model/FleetControlPageContext';
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
  const { handleMoveVehicleOnRoute } = useFleetControlPageContext();

  const { fleetControlData, places } = useFleetControlPageDataSource();

  const [assignmentVehicle] = useAssignmentVehicleMutation();

  const confirm = useConfirm();

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

  const onAssignmentVehicle = async ({
    targetKind,
    targetGarageId = null,
    targetRoutePlaceAId = null,
    targetRoutePlaceBId = null,
  }: {
    readonly targetKind: AssignPlaceType;
    readonly targetGarageId?: number | null;
    readonly targetRoutePlaceAId?: number | null;
    readonly targetRoutePlaceBId?: number | null;
  }) => {
    try {
      const response = assignmentVehicle({
        vehicle_id: vehicleId,
        source_kind: currentAssignedPlace,
        source_route_place_a_id: currentRoutePlaceAId,
        source_route_place_b_id: currentRoutePlaceBId,
        source_garage_place_id: currentGarageId,
        target_kind: targetKind,
        target_route_place_a_id: targetRoutePlaceAId,
        target_route_place_b_id: targetRoutePlaceBId,
        target_garage_place_id: targetGarageId,
      }).unwrap();

      await toast.promise(response, {
        loading: { message: 'Перемещение техники' },
        success: { message: 'Техника перемещена' },
        error: { message: 'Ошибка перемещения' },
      });
    } finally {
      onClose();
    }
  };

  const handleAssignment = async ({
    targetKind,
    targetGarageId = null,
    targetRoutePlaceAId = null,
    targetRoutePlaceBId = null,
  }: {
    readonly targetKind: AssignPlaceType;
    readonly targetGarageId?: number | null;
    readonly targetRoutePlaceAId?: number | null;
    readonly targetRoutePlaceBId?: number | null;
  }) => {
    const currentPlaceLoad = places.find((place) => place.id === currentRoutePlaceAId);
    const currentPlaceUnload = places.find((place) => place.id === currentRoutePlaceBId);
    const currentGarage = places.find((place) => place.id === currentGarageId);
    const targetPlaceLoad = places.find((place) => place.id === targetRoutePlaceAId) ?? null;
    const targetPlaceUnload = places.find((place) => place.id === targetRoutePlaceBId) ?? null;
    const targetGarage = places.find((place) => place.id === targetGarageId);

    let isConfirmed: unknown = false;

    if (currentAssignedPlace === 'ROUTE' && targetKind === 'NO_TASK') {
      isConfirmed = await confirm({
        title: `Вы хотите отменить для ${vehicleName} маршрут «${currentPlaceLoad?.name} — ${currentPlaceUnload?.name}»?`,
        confirmText: 'Да',
        cancelText: 'Отмена',
        size: 'md',
      });
    }

    if (currentAssignedPlace === 'ROUTE' && targetKind === 'GARAGE') {
      isConfirmed = await confirm({
        title: `Вы хотите переместить ${vehicleName} с маршрута «${currentPlaceLoad?.name} — ${currentPlaceUnload?.name}» в «${targetGarage?.name}»?`,
        confirmText: 'Переместить',
        cancelText: 'Отмена',
        size: 'md',
      });
    }

    if (currentAssignedPlace === 'GARAGE' && targetKind === 'GARAGE') {
      isConfirmed = await confirm({
        title: `Вы хотите переместить ${vehicleName} из «${currentGarage?.name}» в «${targetGarage?.name}»?`,
        confirmText: 'Переместить',
        cancelText: 'Отмена',
        size: 'md',
      });
    }

    if (currentAssignedPlace === 'NO_TASK' && targetKind === 'GARAGE') {
      isConfirmed = await confirm({
        title: `Вы хотите переместить ${vehicleName} в «${targetGarage?.name}»?`,
        confirmText: 'Переместить',
        cancelText: 'Отмена',
        size: 'md',
      });
    }

    if (currentAssignedPlace === 'ROUTE' && targetKind === 'ROUTE') {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} с маршрута «${currentPlaceLoad?.name} — ${currentPlaceUnload?.name}» на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () => onAssignmentVehicle({ targetKind, targetRoutePlaceAId, targetRoutePlaceBId }),
      });
    }

    if (currentAssignedPlace === 'GARAGE' && targetKind === 'ROUTE') {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () => onAssignmentVehicle({ targetKind, targetRoutePlaceAId, targetRoutePlaceBId }),
      });
    }

    if (currentAssignedPlace === 'NO_TASK' && targetKind === 'ROUTE') {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () => onAssignmentVehicle({ targetKind, targetRoutePlaceAId, targetRoutePlaceBId }),
      });
    }

    if (isConfirmed) {
      await onAssignmentVehicle({ targetKind, targetGarageId, targetRoutePlaceAId, targetRoutePlaceBId });
    }
  };

  return (
    <div className={styles.root}>
      {currentAssignedPlace === 'ROUTE' && (
        <>
          <div
            className={styles.menu_item}
            onClick={() => handleAssignment({ targetKind: 'NO_TASK' })}
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
              onClick={() => handleAssignment({ targetKind: 'GARAGE', targetGarageId: garage.id })}
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

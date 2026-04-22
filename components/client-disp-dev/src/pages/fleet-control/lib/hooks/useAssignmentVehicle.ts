import { type AssignPlaceType, useAssignmentVehicleMutation } from '@/shared/api/endpoints/fleet-control';
import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { toast } from '@/shared/ui/Toast';

import { useFleetControlPageContext } from '../../model/FleetControlPageContext';

import { useFleetControlPageDataSource } from './useFleetControlPageDataSource';

/**
 * Представляет аргументы хука для перемещения оборудования.
 */
interface UseAssignmentVehicleArgs {
  /** Возвращает делегат, вызываемый при закрытии контекстного меню. */
  readonly onClose: () => void;
}

/**
 * Хук для перемещения оборудования.
 */
export function useAssignmentVehicle(args?: UseAssignmentVehicleArgs) {
  const { handleMoveVehicleOnRoute } = useFleetControlPageContext();

  const { places } = useFleetControlPageDataSource();

  const [assignmentVehicle] = useAssignmentVehicleMutation();

  const confirm = useConfirm();

  const onAssignmentVehicle = async ({
    vehicleId,
    currentAssignedPlace,
    currentRoutePlaceAId,
    currentRoutePlaceBId,
    currentGarageId,
    targetKind,
    targetGarageId,
    targetRoutePlaceAId,
    targetRoutePlaceBId,
  }: {
    readonly vehicleId: number;
    readonly currentAssignedPlace: AssignPlaceType;
    readonly currentGarageId: number | null;
    readonly currentRoutePlaceAId: number | null;
    readonly currentRoutePlaceBId: number | null;
    readonly targetKind: AssignPlaceType;
    readonly targetGarageId: number | null;
    readonly targetRoutePlaceAId: number | null;
    readonly targetRoutePlaceBId: number | null;
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
      args?.onClose();
    }
  };

  return async function ({
    vehicleId,
    vehicleName,
    currentAssignedPlace,
    currentGarageId = null,
    currentRoutePlaceAId = null,
    currentRoutePlaceBId = null,
    targetKind,
    targetGarageId = null,
    targetRoutePlaceAId = null,
    targetRoutePlaceBId = null,
  }: {
    readonly vehicleId: number;
    readonly vehicleName: string;
    readonly currentAssignedPlace: AssignPlaceType;
    readonly currentGarageId: number | null;
    readonly currentRoutePlaceAId: number | null;
    readonly currentRoutePlaceBId: number | null;
    readonly targetKind: AssignPlaceType;
    readonly targetGarageId?: number | null;
    readonly targetRoutePlaceAId?: number | null;
    readonly targetRoutePlaceBId?: number | null;
  }) {
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

    if (
      currentAssignedPlace === 'GARAGE' &&
      targetKind === 'GARAGE' &&
      isCorrectMoveBetweenGarages(currentGarageId, targetGarageId)
    ) {
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

    if (
      currentAssignedPlace === 'ROUTE' &&
      targetKind === 'ROUTE' &&
      isCorrectMoveBetweenRoutes(currentRoutePlaceAId, targetRoutePlaceAId, currentRoutePlaceBId, targetRoutePlaceBId)
    ) {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} с маршрута «${currentPlaceLoad?.name} — ${currentPlaceUnload?.name}» на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () =>
          onAssignmentVehicle({
            vehicleId,
            currentAssignedPlace,
            currentRoutePlaceAId,
            currentRoutePlaceBId,
            currentGarageId,
            targetKind,
            targetGarageId,
            targetRoutePlaceAId,
            targetRoutePlaceBId,
          }),
      });
    }

    if (currentAssignedPlace === 'GARAGE' && targetKind === 'ROUTE') {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () =>
          onAssignmentVehicle({
            vehicleId,
            currentAssignedPlace,
            currentRoutePlaceAId,
            currentRoutePlaceBId,
            currentGarageId,
            targetKind,
            targetGarageId,
            targetRoutePlaceAId,
            targetRoutePlaceBId,
          }),
      });
    }

    if (currentAssignedPlace === 'NO_TASK' && targetKind === 'ROUTE') {
      handleMoveVehicleOnRoute({
        vehicleId,
        targetPlaceLoad,
        targetPlaceUnload,
        title: `Вы хотите переместить ${vehicleName} на маршрут «${targetPlaceLoad?.name} — ${targetPlaceUnload?.name}»?`,
        moveFn: () =>
          onAssignmentVehicle({
            vehicleId,
            currentAssignedPlace,
            currentRoutePlaceAId,
            currentRoutePlaceBId,
            currentGarageId,
            targetKind,
            targetGarageId,
            targetRoutePlaceAId,
            targetRoutePlaceBId,
          }),
      });
    }

    if (isConfirmed) {
      await onAssignmentVehicle({
        vehicleId,
        currentAssignedPlace,
        currentRoutePlaceAId,
        currentRoutePlaceBId,
        currentGarageId,
        targetKind,
        targetGarageId,
        targetRoutePlaceAId,
        targetRoutePlaceBId,
      });
    }
  };
}

/**
 * Проверяет корректность перемещения техники между гаражами.
 *
 * @param currentGarageId идентификатор текущего гаража.
 * @param targetGarageId идентификатор целевого гаража.
 */
function isCorrectMoveBetweenGarages(currentGarageId: number | null, targetGarageId: number | null) {
  if (!hasValue(currentGarageId) || !hasValue(targetGarageId)) {
    return false;
  }

  return currentGarageId !== targetGarageId;
}

/**
 * Проверяет корректность перемещения техники между маршрутами.
 *
 * @param currentRoutePlaceAId идентификатор текущего пункта погрузки.
 * @param targetRoutePlaceAId идентификатор целевого пункта погрузки.
 * @param currentRoutePlaceBId идентификатор текущего пункта разгрузки.
 * @param targetRoutePlaceBId идентификатор целевого пункта разгрузки.
 */
function isCorrectMoveBetweenRoutes(
  currentRoutePlaceAId: number | null,
  targetRoutePlaceAId: number | null,
  currentRoutePlaceBId: number | null,
  targetRoutePlaceBId: number | null,
) {
  if (
    !hasValue(currentRoutePlaceAId) ||
    !hasValue(targetRoutePlaceAId) ||
    !hasValue(currentRoutePlaceBId) ||
    !hasValue(targetRoutePlaceBId)
  ) {
    return false;
  }

  return currentRoutePlaceAId !== targetRoutePlaceAId || currentRoutePlaceBId !== targetRoutePlaceBId;
}

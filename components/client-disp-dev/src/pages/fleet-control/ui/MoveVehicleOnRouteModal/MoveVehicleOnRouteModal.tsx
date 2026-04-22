import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useMemo, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

import { calculateFromTrips, calculateFromVolume, calculateFromWeight } from '@/entities/route-task';

import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import {
  type RouteTaskUpsertItem,
  TypeTask,
  useCreateRouteTaskMutation,
  useGetAllTasksQuery,
  useUpdateRouteTaskMutation,
} from '@/shared/api/endpoints/route-tasks';
import { useGetVehicleByIdQuery } from '@/shared/api/endpoints/vehicles';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { POSITIVE_NUMBER_VALIDATION } from '@/shared/lib/validation';
import { ConfirmModal } from '@/shared/ui/ConfirmModal';
import { ErrorMessage } from '@/shared/ui/ErrorMessage';
import { NumberInput } from '@/shared/ui/NumberInput';

import { useFleetControlPageContext } from '../../model/FleetControlPageContext';
import type { MovingVehicle } from '../../model/moving-vehicle';

import styles from './MoveVehicleOnRouteModal.module.css';

const ValidationShema = z.object({
  volume: POSITIVE_NUMBER_VALIDATION,
  weight: POSITIVE_NUMBER_VALIDATION,
  plannedTripsCount: POSITIVE_NUMBER_VALIDATION,
});

/** Представляет состояние формы. */
type FormState = z.infer<typeof ValidationShema>;

/**
 * Представляет свойства компонента модального окна для перемещения оборудования на маршрут.
 */
interface MoveVehicleOnRouteModalProps {
  readonly movingVehicle: MovingVehicle;
}

/**
 * Представляет компонент модального окна для перемещения оборудования на маршрут.
 */
export function MoveVehicleOnRouteModal({ movingVehicle }: MoveVehicleOnRouteModalProps) {
  const { handleMoveVehicleOnRoute } = useFleetControlPageContext();

  const targetPlaceLoadId = movingVehicle.targetPlaceLoad?.id ?? null;

  const { data: cargoData } = useGetAllLoadTypeQuery();
  const { data: vehicleData } = useGetVehicleByIdQuery(movingVehicle.vehicleId);

  const placeLoadCargo = useMemo(() => {
    const placeLoadCargoType = movingVehicle.targetPlaceLoad?.cargo_type;
    if (hasValue(placeLoadCargoType)) {
      return cargoData?.entities[placeLoadCargoType];
    }
  }, [cargoData?.entities, movingVehicle.targetPlaceLoad?.cargo_type]);

  const paramsToCalculateLinkedFields = useMemo(() => {
    if (
      hasValue(placeLoadCargo?.density) &&
      hasValue(vehicleData?.model?.load_capacity_tons) &&
      hasValue(vehicleData?.model?.volume_m3)
    ) {
      return {
        density: placeLoadCargo.density,
        loadCapacity: vehicleData.model.load_capacity_tons,
        volumeM3: vehicleData.model.volume_m3,
      };
    }
  }, [placeLoadCargo?.density, vehicleData?.model?.load_capacity_tons, vehicleData?.model?.volume_m3]);

  const { data } = useGetAllTasksQuery({
    vehicle_id: movingVehicle.vehicleId,
    place_a_id: targetPlaceLoadId,
    place_b_id: movingVehicle.targetPlaceUnload?.id,
  });

  const routeTask = useMemo(() => data?.items.at(0), [data?.items]);

  const [createRouteTask, { isLoading: isLoadingCreateRouteTask }] = useCreateRouteTaskMutation();
  const [updateRouteTask, { isLoading: isLoadingUpdateRouteTask }] = useUpdateRouteTaskMutation();

  const [createUpdateRouteTaskError, setCreateUpdateRouteTaskError] = useState<string | null>(null);

  const {
    control,
    reset,
    getValues,
    setValue,
    trigger,
    formState: { isValid },
  } = useForm<FormState>({
    mode: 'onChange',
    defaultValues: { volume: '', weight: '', plannedTripsCount: '' },
    resolver: zodResolver(ValidationShema),
  });

  useEffect(() => {
    if (routeTask) {
      reset({
        volume: routeTask.volume ?? 0,
        weight: routeTask.weight ?? 0,
        plannedTripsCount: routeTask.planned_trips_count,
      });
    }
  }, [reset, routeTask]);

  const onCreateRouteTask = async (task: RouteTaskUpsertItem) => {
    try {
      await createRouteTask(task).unwrap();
    } catch {
      setCreateUpdateRouteTaskError('Возникла ошибка при создании маршрутного задания.');
    }
  };

  const onUpdateRouteTask = async (id: string, task: RouteTaskUpsertItem) => {
    try {
      await updateRouteTask({ id, body: task }).unwrap();
    } catch {
      setCreateUpdateRouteTaskError('Возникла ошибка при изменении маршрутного задания.');
    }
  };

  const onConfirm = async () => {
    const currentState = getValues();

    assertHasValue(targetPlaceLoadId);
    assertHasValue(movingVehicle.targetPlaceUnload?.id);

    const draftTask = {
      place_a_id: targetPlaceLoadId,
      place_b_id: movingVehicle.targetPlaceUnload.id,
      type_task: TypeTask.LOADING_GM,
      volume: Number(currentState.volume),
      weight: Number(currentState.weight),
      planned_trips_count: Number(currentState.plannedTripsCount),
      vehicle_id: movingVehicle.vehicleId,
    };

    if (routeTask) {
      await onUpdateRouteTask(routeTask.id, draftTask);
    } else {
      await onCreateRouteTask(draftTask);
    }
    handleMoveVehicleOnRoute(null);
    movingVehicle.moveFn();
  };

  const isLoading = isLoadingCreateRouteTask || isLoadingUpdateRouteTask;

  const inputsDisabled = isLoading || !hasValue(paramsToCalculateLinkedFields);

  return (
    <ConfirmModal
      isOpen={true}
      onClose={() => handleMoveVehicleOnRoute(null)}
      onConfirm={onConfirm}
      title={movingVehicle?.title}
      confirmButtonText="Переместить"
      message="Необходимо указать объем работ"
      isLoading={isLoading}
      disabledConfirm={!isValid}
    >
      <form className={styles.form}>
        <Controller
          control={control}
          name="volume"
          render={({ field, fieldState }) => (
            <NumberInput
              {...field}
              withAsterisk
              label="Объем, м³"
              error={fieldState.error?.message}
              disabled={inputsDisabled}
              hideControls
              labelPosition="vertical"
              variant="combobox-primary"
              onChange={(value) => {
                field.onChange(value);
                if (paramsToCalculateLinkedFields) {
                  const { weight, plannedTripsCount } = calculateFromVolume(
                    hasValueNotEmpty(value) ? Number(value) : null,
                    paramsToCalculateLinkedFields,
                  );

                  setValue('weight', weight ?? '');
                  setValue('plannedTripsCount', plannedTripsCount ?? '');

                  void trigger(['weight', 'plannedTripsCount']);
                }
              }}
            />
          )}
        />
        <Controller
          control={control}
          name="weight"
          render={({ field, fieldState }) => (
            <NumberInput
              {...field}
              withAsterisk
              label="Вес, т"
              error={fieldState.error?.message}
              disabled={inputsDisabled}
              hideControls
              labelPosition="vertical"
              variant="combobox-primary"
              onChange={(value) => {
                field.onChange(value);
                if (paramsToCalculateLinkedFields) {
                  const { volume, plannedTripsCount } = calculateFromWeight(
                    hasValueNotEmpty(value) ? Number(value) : null,
                    paramsToCalculateLinkedFields,
                  );

                  setValue('volume', volume ?? '');
                  setValue('plannedTripsCount', plannedTripsCount ?? '');

                  void trigger(['volume', 'plannedTripsCount']);
                }
              }}
            />
          )}
        />
        <Controller
          control={control}
          name="plannedTripsCount"
          render={({ field, fieldState }) => (
            <NumberInput
              {...field}
              withAsterisk
              label="Рейсов"
              error={fieldState.error?.message}
              disabled={inputsDisabled}
              hideControls
              labelPosition="vertical"
              variant="combobox-primary"
              onChange={(value) => {
                field.onChange(value);
                if (paramsToCalculateLinkedFields) {
                  const { volume, weight } = calculateFromTrips(
                    hasValueNotEmpty(value) ? Number(value) : null,
                    paramsToCalculateLinkedFields,
                  );

                  setValue('volume', volume ?? '');
                  setValue('weight', weight ?? '');

                  void trigger(['volume', 'weight']);
                }
              }}
            />
          )}
        />
      </form>
      {hasValue(createUpdateRouteTaskError) && <ErrorMessage message={createUpdateRouteTaskError} />}
    </ConfirmModal>
  );
}

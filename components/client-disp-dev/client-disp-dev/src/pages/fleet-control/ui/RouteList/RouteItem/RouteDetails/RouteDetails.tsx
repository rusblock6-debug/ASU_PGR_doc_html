import { useEffect } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';

import {
  type RouteDraftFleetControl,
  type RouteFleetControl,
  useCreateRouteMutation,
  useUpdateRouteMutation,
} from '@/shared/api/endpoints/fleet-control';
import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import {
  isLoadPlace,
  isUnloadPlace,
  type LoadPlace,
  type UnloadPlace,
  useUpdatePlaceMutation,
} from '@/shared/api/endpoints/places';
import type { Vehicle } from '@/shared/api/endpoints/vehicles';
import { cn } from '@/shared/lib/classnames-utils';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { convertToNumberOrNull } from '@/shared/lib/format-number';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useDebouncedCallback } from '@/shared/lib/hooks/useDebouncedCallback';
import { NumberInput } from '@/shared/ui/NumberInput';
import { Select } from '@/shared/ui/Select';
import { toast } from '@/shared/ui/Toast';

import { useFleetControlPageDataSource } from '../../../../lib/hooks/useFleetControlPageDataSource';
import { FLEET_CONTROL_MODE } from '../../../../lib/types/fleet-conntrol-mode';
import { useFleetControlPageContext } from '../../../../model/FleetControlPageContext';

import styles from './RouteDetails.module.css';
import { RouteVehicles } from './RouteVehicles';

/** Представляет состояние формы. */
interface FormState {
  /** Возвращает место погрузки. */
  readonly loadPlace: string;
  /** Возвращает вид груза в месте погрузки. */
  readonly loadCargoType: string;
  /** Возвращает остаток в месте погрузки. */
  readonly loadVolume?: number;
  /** Возвращает горизонт места погрузки. */
  readonly loadHorizon: string;
  /** Возвращает список оборудования на маршруте. */
  readonly vehicles: readonly Vehicle[];
  /** Возвращает место разгрузки. */
  readonly unLoadPlace: string;
  /** Возвращает вид груза в месте разгрузки. */
  readonly unLoadCargoType: string;
  /** Возвращает остаток в месте разгрузки. */
  readonly unLoadVolume?: number;
  /** Возвращает горизонт места разгрузки. */
  readonly unLoadHorizon: string;
}

/**
 * Представляет свойства компонента детальной информации о маршруте.
 */
interface RouteDetailsProps {
  /** Возвращает маршрут. */
  readonly route: RouteFleetControl | RouteDraftFleetControl;
  /** Возвращает сообщение о предупреждении. */
  readonly cargoTypeRouteWarning: string | null;
  /** Возвращает делегат, вызываемый для установки сообщения о предупреждении. */
  readonly setCargoTypeRouteWarning: (value: string | null) => void;
  /** Возвращает делегат, вызываемый для установки сообщения об ошибке. */
  readonly showRouteError: (value: string) => void;
}

/**
 * Представляет компонент детальной информации о маршруте.
 */
export function RouteDetails({
  route,
  cargoTypeRouteWarning,
  setCargoTypeRouteWarning,
  showRouteError,
}: RouteDetailsProps) {
  const { fleetControlMode, handleRemoveNewRoute } = useFleetControlPageContext();

  const isHorizontalMode = fleetControlMode === FLEET_CONTROL_MODE.HORIZONTAL;

  const { places } = useFleetControlPageDataSource();
  const { data: cargoData } = useGetAllLoadTypeQuery();
  const { data: horizonsData } = useGetAllHorizonsQuery();

  const [updatePlace] = useUpdatePlaceMutation();
  const [createRoute] = useCreateRouteMutation();
  const [updateRoute] = useUpdateRouteMutation();

  const placeLoadOptions = places
    .filter((item) => item.type === 'load')
    .map((item) => ({ value: String(item.id), label: item.name }));

  const placeUnloadOptions = places
    .filter((item) => item.type === 'unload')
    .map((item) => ({ value: String(item.id), label: item.name }));

  const cargoOptions = Object.values(cargoData?.entities ?? {}).map((item) => ({
    value: String(item.id),
    label: item.name,
  }));

  const horizons = horizonsData?.items?.length ? horizonsData.items : EMPTY_ARRAY;

  const horizonsOptions = horizons.map((item) => ({
    value: String(item.id),
    label: item.name,
  }));

  const methods = useForm<FormState>({
    mode: 'onChange',
    defaultValues: {
      loadPlace: hasValue(route.place_a_id) ? String(route.place_a_id) : undefined,
      unLoadPlace: hasValue(route.place_b_id) ? String(route.place_b_id) : undefined,
    },
  });

  const { control, setValue } = methods;

  const [loadCargoType, unLoadCargoType, loadPlaceId, unLoadPlaceId] = useWatch({
    control,
    name: ['loadCargoType', 'unLoadCargoType', 'loadPlace', 'unLoadPlace'],
  });

  useEffect(() => {
    const loadPlace = places.find((p) => p.id === convertToNumberOrNull(loadPlaceId));
    const unloadPlace = places.find((p) => p.id === convertToNumberOrNull(unLoadPlaceId));

    setValue('loadCargoType', hasValue(loadPlace?.cargo_type) ? String(loadPlace.cargo_type) : '');

    setValue(
      'loadVolume',
      isLoadPlace(loadPlace) && hasValue(loadPlace.current_stock) ? loadPlace.current_stock : undefined,
    );

    setValue('loadHorizon', hasValue(loadPlace?.horizon_id) ? String(loadPlace.horizon_id) : '');

    setValue('unLoadCargoType', hasValue(unloadPlace?.cargo_type) ? String(unloadPlace.cargo_type) : '');

    setValue(
      'unLoadVolume',
      isUnloadPlace(unloadPlace) && hasValue(unloadPlace.current_stock) ? unloadPlace.current_stock : undefined,
    );

    setValue('unLoadHorizon', hasValue(unloadPlace?.horizon_id) ? String(unloadPlace.horizon_id) : '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [places]);

  useEffect(() => {
    if (hasValueNotEmpty(loadCargoType) && hasValueNotEmpty(unLoadCargoType) && loadCargoType !== unLoadCargoType) {
      setCargoTypeRouteWarning('Разные виды груза');
      return;
    }
    setCargoTypeRouteWarning(null);
  }, [loadCargoType, setCargoTypeRouteWarning, unLoadCargoType]);

  const debouncedSubmit = useDebouncedCallback(500);

  const handleEditRoute = async (args: { newLoadPlaceId?: string | null; newUnLoadPlaceId?: string | null }) => {
    const newLoadPlaceId = convertToNumberOrNull(hasValue(args.newLoadPlaceId) ? args.newLoadPlaceId : loadPlaceId);
    const newUnLoadPlaceId = convertToNumberOrNull(
      hasValue(args.newUnLoadPlaceId) ? args.newUnLoadPlaceId : unLoadPlaceId,
    );
    if (hasValue(newLoadPlaceId) && hasValue(newUnLoadPlaceId)) {
      if (route.route_id === 'DRAFT_ROUTE') {
        try {
          const request = createRoute({ place_a_id: newLoadPlaceId, place_b_id: newUnLoadPlaceId }).unwrap();

          await toast.promise(request, {
            loading: { message: 'Создание нового маршрута' },
            success: { message: 'Создан новый маршрут' },
            error: { message: 'Ошибка создания сохранения' },
          });

          handleRemoveNewRoute();
        } catch {
          showRouteError('Произошла ошибка при создании маршрута');
        }
        return;
      }
      if (hasValue(route.place_a_id) && hasValue(route.place_b_id)) {
        try {
          await updateRoute({
            from_place_a_id: route.place_a_id,
            from_place_b_id: route.place_b_id,
            to_place_a_id: newLoadPlaceId,
            to_place_b_id: newUnLoadPlaceId,
          }).unwrap();
        } catch {
          showRouteError('Произошла ошибка при изменении маршрута');
          setValue('loadPlace', String(route.place_a_id));
          setValue('unLoadPlace', String(route.place_b_id));
        }
      }
    }
  };

  const handleEditPlace = async <K extends keyof T, T extends LoadPlace | UnloadPlace>(
    placeId: string,
    field: K,
    value: T[K],
  ) => {
    const id = convertToNumberOrNull(placeId);
    const place = places.find((p) => p.id === id);

    if (!place || !id) {
      return;
    }

    const request = updatePlace({
      placeId: id,
      body: { ...place, [field]: value },
    }).unwrap();

    await toast.promise(request, {
      loading: { message: 'Сохранение изменений' },
      success: { message: 'Изменения сохранены' },
      error: { message: 'Ошибка сохранения' },
    });
  };

  return (
    <form className={cn(styles.root, { [styles.vertical]: !isHorizontalMode })}>
      <div className={cn(styles.load_place_container, { [styles.vertical]: !isHorizontalMode })}>
        <Controller
          name="loadPlace"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              variant="combobox-primary"
              data={placeLoadOptions}
              onChange={(value) => {
                const selectedPlace = places.find((item) => item.id === Number(value));
                if (hasValue(selectedPlace?.cargo_type)) {
                  const cargoType = cargoData?.entities[selectedPlace.cargo_type].id;
                  if (hasValue(cargoType)) {
                    setValue('loadCargoType', String(cargoType));
                  }

                  const horizonId = selectedPlace.horizon_id;
                  setValue('loadHorizon', String(horizonId));

                  const currentStock =
                    isLoadPlace(selectedPlace) && hasValue(selectedPlace.current_stock)
                      ? selectedPlace.current_stock
                      : undefined;
                  setValue('loadVolume', currentStock);
                }

                field.onChange(value);
                debouncedSubmit(() => handleEditRoute({ newLoadPlaceId: value }));
              }}
              label={isHorizontalMode ? 'Погрузка' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
            />
          )}
        />
        <Controller
          name="loadCargoType"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              variant="combobox-primary"
              data={cargoOptions}
              onChange={(value) => {
                field.onChange(value);
                const cargoType = convertToNumberOrNull(value);
                if (hasValue(cargoType)) {
                  debouncedSubmit(() => handleEditPlace(loadPlaceId, 'cargo_type', cargoType));
                }
              }}
              label={isHorizontalMode ? 'Вид груза' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
              warning={hasValue(cargoTypeRouteWarning)}
            />
          )}
        />
        <Controller
          control={control}
          name="loadVolume"
          render={({ field, fieldState }) => (
            <NumberInput
              {...field}
              onChange={(value) => {
                field.onChange(Number(value));
                const currentStock = convertToNumberOrNull(value);
                if (hasValue(currentStock)) {
                  debouncedSubmit(() => handleEditPlace(loadPlaceId, 'current_stock', currentStock));
                }
              }}
              variant="combobox-primary"
              label={isHorizontalMode ? 'Остаток, м³' : undefined}
              error={fieldState.error?.message}
              hideControls
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
            />
          )}
        />
        <Controller
          name="loadHorizon"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              data={horizonsOptions}
              label={isHorizontalMode ? 'Горизонт' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
              readOnly
            />
          )}
        />
      </div>
      <RouteVehicles
        route={route}
        isHorizontalMode={isHorizontalMode}
      />
      <div className={cn(styles.unload_place_container, { [styles.vertical]: !isHorizontalMode })}>
        <Controller
          name="unLoadPlace"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              variant="combobox-primary"
              data={placeUnloadOptions}
              onChange={(value) => {
                const selectedPlace = places.find((item) => item.id === Number(value));
                if (hasValue(selectedPlace?.cargo_type)) {
                  const cargoType = cargoData?.entities[selectedPlace.cargo_type].id;
                  if (hasValue(cargoType)) {
                    setValue('unLoadCargoType', String(cargoType));
                  }

                  const horizonId = selectedPlace.horizon_id;
                  setValue('unLoadHorizon', String(horizonId));

                  const currentStock =
                    isUnloadPlace(selectedPlace) && hasValue(selectedPlace.current_stock)
                      ? selectedPlace.current_stock
                      : undefined;
                  setValue('unLoadVolume', currentStock);
                }

                field.onChange(value);
                debouncedSubmit(() => handleEditRoute({ newUnLoadPlaceId: value }));
              }}
              label={isHorizontalMode ? 'Разгрузка' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
            />
          )}
        />
        <Controller
          name="unLoadCargoType"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              variant="combobox-primary"
              data={cargoOptions}
              onChange={(value) => {
                field.onChange(value);
                const cargoType = convertToNumberOrNull(value);
                if (hasValue(cargoType)) {
                  debouncedSubmit(() => handleEditPlace(unLoadPlaceId, 'cargo_type', cargoType));
                }
              }}
              label={isHorizontalMode ? 'Вид груза' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
              warning={hasValue(cargoTypeRouteWarning)}
            />
          )}
        />
        <Controller
          control={control}
          name="unLoadVolume"
          render={({ field, fieldState }) => (
            <NumberInput
              {...field}
              onChange={(value) => {
                field.onChange(Number(value));
                const currentStock = convertToNumberOrNull(value);
                if (hasValue(currentStock)) {
                  debouncedSubmit(() => handleEditPlace(unLoadPlaceId, 'current_stock', currentStock));
                }
              }}
              variant="combobox-primary"
              label={isHorizontalMode ? 'Остаток, м³' : undefined}
              error={fieldState.error?.message}
              hideControls
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
            />
          )}
        />
        <Controller
          name="unLoadHorizon"
          control={control}
          render={({ field, fieldState }) => (
            <Select
              {...field}
              data={horizonsOptions}
              label={isHorizontalMode ? 'Горизонт' : undefined}
              error={fieldState.error?.message}
              classNames={{ root: isHorizontalMode ? styles.input_root : undefined }}
              labelPosition={!isHorizontalMode ? 'vertical' : undefined}
              readOnly
            />
          )}
        />
      </div>
    </form>
  );
}

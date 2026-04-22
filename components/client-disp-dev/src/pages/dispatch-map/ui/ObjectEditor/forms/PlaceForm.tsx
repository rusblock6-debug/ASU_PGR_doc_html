import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useMemo } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { PLACE_TYPES, placeTypeOptions } from '@/entities/place';

import { useGetAllHorizonsQuery, useLazyGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import { type Place, useCreatePlaceMutation, useUpdatePlaceMutation } from '@/shared/api/endpoints/places';
import DoneIcon from '@/shared/assets/icons/ic-circle-check-big.svg?react';
import WarningIcon from '@/shared/assets/icons/ic-triangle-alert.svg?react';
import { convertToNumberOrNull } from '@/shared/lib/format-number';
import { hasValue, hasValueNotEmpty } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { NUMBER_OPTIONAL_VALIDATION, SELECT_VALIDATION, STRING_VALIDATION } from '@/shared/lib/validation';
import { Alert } from '@/shared/ui/Alert';
import { AppButton } from '@/shared/ui/AppButton';
import { toast } from '@/shared/ui/Toast';

import { mapActions } from '../../..';
import { fromScene } from '../../../lib/coordinates';
import { selectPlacementPlaceToAdd, selectSelectedHorizonId } from '../../../model/selectors';
import { CoordinatesField } from '../FormFields/CoordinatesField';
import { DateField } from '../FormFields/DateField';
import { NumberField } from '../FormFields/NumberField';
import { SelectField } from '../FormFields/SelectField';
import { TextField } from '../FormFields/TextField';
import { FormHeader } from '../FormHeader';

import styles from './Form.module.css';

const ValidationShema = z
  .object({
    name: STRING_VALIDATION,
    placeType: z.enum(PLACE_TYPES),
    capacity: NUMBER_OPTIONAL_VALIDATION,
    startDate: z.string().trim().nullable().optional(),
    endDate: STRING_VALIDATION.optional().nullable(),
    currentStock: NUMBER_OPTIONAL_VALIDATION,
    horizonId: SELECT_VALIDATION.optional().nullable(),
    cargoType: SELECT_VALIDATION.optional().nullable(),
    nodeId: z.number().nullable().optional(),
    x: NUMBER_OPTIONAL_VALIDATION,
    y: NUMBER_OPTIONAL_VALIDATION,
  })
  .superRefine((data, ctx) => {
    const isParkTransit = data.placeType === 'park' || data.placeType === 'transit';

    if (!isParkTransit && !data.startDate) {
      ctx.addIssue({
        code: 'custom',
        message: 'Заполните поле',
        path: ['startDate'],
      });
    }
  });

/** Представляет состояние формы. */
type FormState = z.infer<typeof ValidationShema>;

/**
 * Представляет свойства компонента формы для создания или редактирования мест.
 */
interface PlaceFormProps {
  /** Возвращает делегат, вызываемый при закрытии. */
  readonly onClose: (fn: () => void) => void;
  /** Возвращает редактируемое место. */
  readonly place?: Place;
}

/**
 * Представляет компонент формы для создания или редактирования мест.
 */
export function PlaceForm({ onClose, place }: PlaceFormProps) {
  const dispatch = useAppDispatch();
  const placementPlaceToAdd = useAppSelector(selectPlacementPlaceToAdd);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);

  const { data: cargoData } = useGetAllLoadTypeQuery();
  const { data: horizonsData } = useGetAllHorizonsQuery();

  const [createPlace, { isLoading: isLoadingCreatePlace }] = useCreatePlaceMutation();
  const [updatePlace, { isLoading: isLoadingUpdatePlace }] = useUpdatePlaceMutation();

  const [fetchGraph, { isFetching: isFetchingGraph }] = useLazyGetHorizonGraphQuery();

  const horizonsOptions = useMemo(() => {
    if (horizonsData) {
      return Array.from(horizonsData.items)
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((item) => ({
          value: String(item.id),
          label: item.name,
        }));
    }
    return [];
  }, [horizonsData]);

  const cargoOptions = cargoData
    ? cargoData.ids
        .map((id) => {
          const item = cargoData.entities[id];
          return { value: String(item.id), label: item.name };
        })
        .sort((a, b) => a.label.localeCompare(b.label))
    : [];

  const methods = useForm<FormState>({
    mode: 'onChange',
    defaultValues: getFormDefaultValues(place),
    resolver: zodResolver(ValidationShema),
  });

  const {
    control,
    handleSubmit,
    reset,
    formState: { isDirty, isValid },
    setValue,
  } = methods;

  const [minStartDate, maxEndDate, placeType, nodeId] = useWatch({
    control,
    name: ['startDate', 'endDate', 'placeType', 'nodeId'],
  });

  const isParkTransitPlace = placeType === 'park' || placeType === 'transit';
  const isUnloadReloadPlace = placeType === 'unload' || placeType === 'reload';

  const handlePlacementClick = () => {
    if (placementPlaceToAdd?.isPlacementMode) {
      dispatch(mapActions.setPlacementPlaceToAdd(null));
    } else {
      dispatch(mapActions.setPlacementPlaceToAdd({ placeType, position: null, isPlacementMode: true, nodeId: null }));
    }
  };

  const clearPlacement = () => {
    setValue('x', '', { shouldValidate: true, shouldDirty: true });
    setValue('y', '', { shouldValidate: true, shouldDirty: true });
    setValue('nodeId', null, { shouldDirty: true });
    dispatch(mapActions.setPlacementPlaceToAdd(null));
  };

  const handleClearPlacement = () => {
    clearPlacement();
    setValue('horizonId', null, { shouldDirty: true });
  };

  const handleHorizonChange = () => {
    if (hasValue(nodeId)) {
      clearPlacement();
    }
  };

  useEffect(() => {
    reset(getFormDefaultValues(place));
  }, [reset, place]);

  useEffect(() => {
    dispatch(mapActions.setHasUnsavedChanges(isDirty));
  }, [dispatch, isDirty]);

  useEffect(() => {
    if (placementPlaceToAdd?.position) {
      const coordinates = fromScene(placementPlaceToAdd.position[0], placementPlaceToAdd.position[2]);
      setValue('x', coordinates.lon, { shouldValidate: true, shouldDirty: true });
      setValue('y', coordinates.lat, { shouldValidate: true, shouldDirty: true });
      setValue('nodeId', placementPlaceToAdd.nodeId, { shouldDirty: true });

      if (hasValue(selectedHorizonId)) {
        setValue('horizonId', String(selectedHorizonId), { shouldDirty: true });
      }
    }
  }, [placementPlaceToAdd, selectedHorizonId, setValue]);

  useEffect(() => {
    if (placementPlaceToAdd && placementPlaceToAdd.placeType !== placeType) {
      dispatch(mapActions.setPlacementPlaceToAdd({ ...placementPlaceToAdd, placeType }));
    }
  }, [dispatch, placeType, placementPlaceToAdd]);

  const onSubmit = async (data: FormState) => {
    try {
      if (place) {
        await updatePlace({
          placeId: place.id,
          body: getRequestDTO(data),
        }).unwrap();
      } else {
        await createPlace(getRequestDTO(data)).unwrap();
      }
    } catch {
      toast.error({ message: place ? 'Ошибка сохранения' : 'Ошибка добавления' });
      return;
    }

    if (hasValue(selectedHorizonId)) {
      await fetchGraph(selectedHorizonId).unwrap();
    }

    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
    dispatch(mapActions.setPlacementPlaceToAdd(null));

    toast.success({
      message: place ? 'Изменения сохранены' : `Добавлено новое место «${data.name}»`,
    });
  };

  const onFormClose = () => {
    onClose(() => {
      dispatch(mapActions.setPlacementPlaceToAdd(null));
    });
  };

  const isLoading = isLoadingCreatePlace || isLoadingUpdatePlace || isFetchingGraph;

  const disabledSubmitButton = !isDirty || !isValid;

  return (
    <>
      <FormHeader
        title={place?.name ?? 'Новый объект'}
        onClose={onFormClose}
      />
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className={styles.form}
        >
          <div className={styles.inputs_container}>
            <TextField
              name="name"
              label="Наименование"
              required
              disabled={isLoading}
            />
            <SelectField
              allowDeselect={false}
              name="placeType"
              label="Тип"
              required
              options={placeTypeOptions}
              disabled={isLoading}
            />
            <CoordinatesField
              xName="x"
              yName="y"
              label="Местоположение"
              readOnly
              disabled={isLoading || !hasValue(placeType)}
              onPlacementClick={handlePlacementClick}
              onClearClick={handleClearPlacement}
            />

            {!isParkTransitPlace && (
              <>
                <DateField
                  required
                  name="startDate"
                  label="Дата ввода в эксплуатацию"
                  maxDate={maxEndDate}
                  disabled={isLoading}
                />
                <DateField
                  name="endDate"
                  label="Дата вывода из эксплуатации"
                  minDate={minStartDate}
                  disabled={isLoading}
                />
                {isUnloadReloadPlace && (
                  <NumberField
                    name="capacity"
                    label="Вместимость, м³"
                    disabled={isLoading}
                  />
                )}
                <NumberField
                  name="currentStock"
                  label="Остаток, м³"
                  disabled={isLoading}
                />
              </>
            )}

            <SelectField
              name="horizonId"
              label="Горизонт"
              options={horizonsOptions}
              disabled={isLoading}
              onChange={handleHorizonChange}
            />

            {!isParkTransitPlace && (
              <SelectField
                name="cargoType"
                label="Вид груза"
                options={cargoOptions}
                disabled={isLoading}
              />
            )}
          </div>

          <Alert
            icon={hasValue(nodeId) ? <DoneIcon /> : <WarningIcon />}
            color={hasValue(nodeId) ? 'green' : 'yellow'}
            variant="outline"
          >
            {getRoadGraphBindingMessage(nodeId, place?.node_id)}
          </Alert>

          <AppButton
            type="submit"
            disabled={disabledSubmitButton}
            loading={isLoading}
            className={styles.submit_button}
          >
            Сохранить
          </AppButton>
        </form>
      </FormProvider>
    </>
  );
}

/** Возвращает текст подсказки о привязке места к вершине графа дорог. */
function getRoadGraphBindingMessage(formNodeId: FormState['nodeId'], savedNodeId?: number | null) {
  if (hasValue(formNodeId)) {
    return `Привязан к графу дорог (вершина №${formNodeId})`;
  }

  if (hasValue(savedNodeId)) {
    return 'Будет отвязан от графа дорог (сохраните изменения)';
  }

  return 'Не привязан к графу дорог';
}

/** Возвращает начальные значения формы. */
function getFormDefaultValues(place?: Place) {
  if (!place) {
    return {
      name: '',
      placeType: PLACE_TYPES[0],
      capacity: null,
      startDate: null,
      endDate: null,
      currentStock: null,
      horizonId: null,
      cargoType: null,
      nodeId: null,
      x: '',
      y: '',
    };
  }

  return {
    name: place.name,
    placeType: place.type,
    capacity: 'capacity' in place ? place.capacity : null,
    startDate: 'start_date' in place ? place.start_date : null,
    endDate: 'end_date' in place ? place.end_date : null,
    currentStock: 'current_stock' in place ? place.current_stock : null,
    horizonId: hasValue(place.horizon_id) ? String(place.horizon_id) : null,
    cargoType: hasValue(place.cargo_type) ? String(place.cargo_type) : null,
    nodeId: place.node_id ?? null,
    x: place.x ?? '',
    y: place.y ?? '',
  };
}

/** Возвращает данные для отправки на сервер. */
function getRequestDTO(data: FormState) {
  const placeType = data.placeType;

  const isParkTransitPlace = placeType === 'park' || placeType === 'transit';
  const isUnloadReloadPlace = placeType === 'unload' || placeType === 'reload';

  return {
    name: data.name,
    type: placeType,
    node_id: data.nodeId ?? null,
    capacity: isUnloadReloadPlace ? convertToNumberOrNull(data.capacity) : null,
    start_date: !isParkTransitPlace ? data.startDate : null,
    end_date: !isParkTransitPlace ? data.endDate : null,
    current_stock: !isParkTransitPlace ? convertToNumberOrNull(data.currentStock) : null,
    cargo_type: !isParkTransitPlace && hasValueNotEmpty(data.cargoType) ? Number(data.cargoType) : null,
  };
}

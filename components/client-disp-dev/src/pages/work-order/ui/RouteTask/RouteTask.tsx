import type { Place } from '@/shared/api/endpoints/places';
import { cn } from '@/shared/lib/classnames-utils';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { ErrorMessage } from '@/shared/ui/ErrorMessage';
import { ExpandableTextarea } from '@/shared/ui/ExpandableTextarea';
import { NumberInput } from '@/shared/ui/NumberInput';
import { Select } from '@/shared/ui/Select';
import type { SelectOption } from '@/shared/ui/types';
import { WarningMessage } from '@/shared/ui/WarningMessage';

import { useDebouncedNumberField } from '../../lib/hooks/useDebouncedNumberField';
import { useDebouncedTextField } from '../../lib/hooks/useDebouncedTextField';
import type { RouteTaskData } from '../../lib/hooks/useRouteTaskData';
import { useTaskFieldState } from '../../lib/hooks/useTaskFieldState';
import { selectMergedVehicleTask } from '../../model/selectors';
import { setPlaceStart, updateTaskField } from '../../model/thunks';
import type { TaskIdentifier } from '../../model/types';
import { RouteStatusBadge } from '../RouteStatusBadge';
import { RouteTaskActions } from '../RouteTaskActions';

import { PlaceSelectField } from './PlaceSelectField';
import { ReadonlyField } from './ReadonlyField';
import styles from './RouteTask.module.css';

const placeFieldClassNames = {
  wrapper: cn(styles.route_task_field, styles.input_medium, styles.route_task_place_wrapper),
  readonlyField: cn(styles.route_task_field, styles.input_medium),
  cargoLabel: cn('truncate', styles.route_task_place),
};

/**
 * Представляет свойства компонента {@link RouteTask}.
 */
interface RouteTaskProps extends TaskIdentifier {
  /** Справочные данные маршрутного задания (места, грузы, опции). */
  readonly routeTaskData: RouteTaskData;
}

/**
 * Представляет компонент карточки маршрутного задания для конкретного транспорта.
 */
export function RouteTask({ vehicleId, taskId, routeTaskData }: RouteTaskProps) {
  const { places, cargoData, placeLoadOptions, placeUnloadOptions, taskTypeOptions } = routeTaskData;

  const dispatch = useAppDispatch();
  const task = useAppSelector((state) => selectMergedVehicleTask(state, vehicleId, taskId));

  const { isBlocked, isLinkedFieldsBlocked, errorMessage, warningMessage, getFieldProps, getFieldPropsWithWarning } =
    useTaskFieldState({
      taskId,
      task,
    });

  const volumeField = useDebouncedNumberField({
    value: task?.volume ?? null,
    field: 'volume',
    vehicleId,
    taskId,
  });

  const weightField = useDebouncedNumberField({
    value: task?.weight ?? null,
    field: 'weight',
    vehicleId,
    taskId,
  });

  const tripsField = useDebouncedNumberField({
    value: task?.plannedTripsCount ?? null,
    field: 'plannedTripsCount',
    vehicleId,
    taskId,
  });

  const messageField = useDebouncedTextField({
    value: task?.message ?? null,
    field: 'message',
    vehicleId,
    taskId,
  });

  const handlePlaceLoadChange = (value: string | null) => {
    const placeLoad = places.find((p) => String(p.id) === value);
    const hasCargo = Boolean(placeLoad?.cargo_type && cargoData?.entities[placeLoad.cargo_type]);

    const placeUnload = places.find((p) => p.id === task?.placeEndId);

    const isUnmatched = isUnmatchedCargoType(placeLoad, placeUnload);

    dispatch(
      setPlaceStart({
        vehicleId,
        taskId,
        placeStartId: value ? Number(value) : null,
        hasCargo,
        isUnmatchedCargoType: isUnmatched,
      }),
    );
  };

  const handlePlaceUnloadChange = (value: string | null) => {
    const placeUnload = places.find((p) => String(p.id) === value);

    const placeLoad = places.find((p) => p.id === task?.placeStartId);

    const isUnmatched = isUnmatchedCargoType(placeLoad, placeUnload);

    dispatch(
      updateTaskField({
        vehicleId,
        taskId,
        field: 'placeEndId',
        value: value ? Number(value) : null,
        isUnmatchedCargoType: isUnmatched,
      }),
    );
  };

  const handleTaskChange = (value: string | null) => {
    dispatch(
      updateTaskField({
        vehicleId,
        taskId,
        field: 'taskType',
        value,
      }),
    );
  };

  if (!task) return null;

  const commonInputProps = {
    variant: 'combobox-primary',
    inputSize: 'combobox-sm',
    labelPosition: 'vertical',
    placeholder: 'Укажите',
  } as const;

  const selectProps = {
    ...commonInputProps,
    placeholder: 'Введите или выберите',
    allowDeselect: false,
    withCheckIcon: false,
    disabled: isBlocked,
    classNames: {
      root: cn(styles.route_task_field, styles.input_medium, {
        [styles.input_label_disabled]: isBlocked,
      }),
    },
  } as const;

  const numberInputProps = {
    ...commonInputProps,
    allowNegative: false,
    withKeyboardEvents: false,
    thousandSeparator: ' ',
    thousandsGroupStyle: 'thousand',
    // запрещаем вводить ноль
    isAllowed: (values: { floatValue?: number }) => values.floatValue !== 0,
    disabled: isLinkedFieldsBlocked,
    classNames: {
      root: cn(styles.route_task_field, styles.input_small, {
        [styles.input_label_disabled]: isLinkedFieldsBlocked,
      }),
    },
  } as const;

  return (
    <div className={styles.route_task}>
      <div className={styles.route_task_header}>
        <div className={styles.route_task_header_info}>
          <RouteStatusBadge status={task?.status} />

          <RouteTaskActions
            vehicleId={vehicleId}
            taskId={taskId}
            task={task}
          />
        </div>

        {errorMessage && (
          <ErrorMessage
            classNames={styles.error_warning_msg}
            message={errorMessage}
          />
        )}

        {!errorMessage && warningMessage && (
          <WarningMessage
            classNames={styles.error_warning_msg}
            message={warningMessage}
          />
        )}
      </div>

      <div className={styles.route_task_body}>
        <PlaceSelectField
          {...getFieldPropsWithWarning('placeStartId')}
          label="Место погрузки"
          isBlocked={isBlocked}
          value={task.placeStartId}
          options={placeLoadOptions}
          selectProps={selectProps}
          cargoName={getCargoName(task.placeStartId, places, cargoData)}
          classNames={placeFieldClassNames}
          onChange={handlePlaceLoadChange}
        />

        <PlaceSelectField
          {...getFieldPropsWithWarning('placeEndId')}
          label="Место разгрузки"
          isBlocked={isBlocked}
          value={task.placeEndId}
          options={placeUnloadOptions}
          selectProps={selectProps}
          cargoName={getCargoName(task.placeEndId, places, cargoData)}
          classNames={placeFieldClassNames}
          onChange={handlePlaceUnloadChange}
        />

        {isBlocked ? (
          <ReadonlyField
            {...getFieldProps('taskType')}
            className={cn(styles.route_task_field, styles.input_medium)}
            label="Тип задания"
            value={findOptionLabel(taskTypeOptions, task.taskType)}
          />
        ) : (
          <Select
            {...selectProps}
            {...getFieldProps('taskType')}
            label="Тип задания"
            data={taskTypeOptions}
            value={task.taskType}
            onChange={handleTaskChange}
            searchable
          />
        )}

        {isLinkedFieldsBlocked ? (
          <ReadonlyField
            {...getFieldProps('volume')}
            className={cn(styles.route_task_field, styles.input_small)}
            label="Объем, м³"
            value={volumeField.value}
          />
        ) : (
          <NumberInput
            {...numberInputProps}
            {...getFieldProps('volume')}
            label="Объем, м³"
            {...volumeField}
          />
        )}

        {isLinkedFieldsBlocked ? (
          <ReadonlyField
            {...getFieldProps('weight')}
            className={cn(styles.route_task_field, styles.input_small)}
            label="Вес, т"
            value={task.weight}
          />
        ) : (
          <NumberInput
            {...numberInputProps}
            {...getFieldProps('weight')}
            label="Вес, т"
            {...weightField}
          />
        )}

        {isLinkedFieldsBlocked ? (
          <ReadonlyField
            {...getFieldProps('plannedTripsCount')}
            className={cn(styles.route_task_field, styles.input_small)}
            label="Рейсов"
            value={task.plannedTripsCount}
          />
        ) : (
          <NumberInput
            {...numberInputProps}
            {...getFieldProps('plannedTripsCount')}
            label="Рейсов"
            min={1}
            allowDecimal={false}
            {...tripsField}
          />
        )}

        {isBlocked ? (
          <ReadonlyField
            className={cn(styles.route_task_field, styles.input_large)}
            label="Комментарий"
            value={task.message}
          />
        ) : (
          <ExpandableTextarea
            {...commonInputProps}
            label="Комментарий"
            classNames={{
              root: cn(styles.route_task_field, styles.input_large, {
                [styles.input_label_disabled]: isBlocked,
              }),
            }}
            maxLength={500}
            maxRows={10}
            disabled={isBlocked}
            {...messageField}
          />
        )}
      </div>
    </div>
  );
}

/** Найти подпись для поля по значению. */
export function findOptionLabel(options: readonly SelectOption[], value: string | null) {
  if (!hasValue(value)) return null;
  return options.find((option) => option.value === value)?.label ?? null;
}

/** Проверяет, что тип груза гарантировано не совпадает по значению. */
function isUnmatchedCargoType(placeLoad?: Place, placeUnload?: Place) {
  return (
    hasValue(placeLoad?.cargo_type) &&
    hasValue(placeUnload?.cargo_type) &&
    placeLoad.cargo_type !== placeUnload.cargo_type
  );
}

/** Получает название груза по идентификатору места. */
function getCargoName(placeId: number | null, places: readonly Place[], cargoData: RouteTaskData['cargoData']) {
  const place = places.find((place) => place.id === placeId);
  if (!hasValue(place?.cargo_type)) return null;
  return cargoData?.entities[place.cargo_type]?.name ?? null;
}

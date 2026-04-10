import { useMemo } from 'react';
import { useForm, Controller } from 'react-hook-form';

import { getPlacesOptionsToSelect } from '@/entities/place';

import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import type { CycleStateHistory, StateHistory } from '@/shared/api/endpoints/state-history';
import { useCreateTripMutation } from '@/shared/api/endpoints/trips';
import { MIN_TRIP_DURATION } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useTimezone } from '@/shared/lib/hooks/useTimezone';
import { AppButton } from '@/shared/ui/AppButton';
import { DateTimePicker } from '@/shared/ui/DateTimePicker';
import { Drawer } from '@/shared/ui/Drawer';
import { Select } from '@/shared/ui/Select';
import { TextInput } from '@/shared/ui/TextInput';
import { toast } from '@/shared/ui/Toast';

import { isValidStatusDurationToAddTrip } from '../../lib/is-valid-status-duration-to-add-trip';
import { useWorkTimeMapPageContext } from '../../model/WorkTimeMapPageContext';

import styles from './AddTripDrawer.module.css';

/** Представляет состояние формы создания рейса. */
interface FormState {
  /** Время начала цикла. ISO 8601 datetime. */
  readonly cycleStartedAt: string;
  /** Время завершения цикла. ISO 8601 datetime. */
  readonly cycleCompletedAt: string;
  /** ID места погрузки (place.id). */
  readonly loadingPlaceId: number;
  /** ID места разгрузки (place.id). */
  readonly unloadingPlaceId: number;
}

/**
 * Представляет свойства компонента для добавления рейса.
 */
interface AddTripDrawer {
  /** Возвращает состояние открытия. */
  readonly isOpen: boolean;
  /** Возвращает делегат вызываемый при закрытии. */
  readonly onClose: () => void;
  /** Возвращает выбранный статус. */
  readonly status: CycleStateHistory;
  /** Возвращает следующий статус (за выбранным). */
  readonly nextStatus: StateHistory | null;
}

/**
 * Представляет компонент для добавления рейса.
 */
export function AddTripDrawer(props: AddTripDrawer) {
  const { isOpen, onClose, status, nextStatus } = props;
  const { vehicles } = useWorkTimeMapPageContext();

  const tz = useTimezone();

  const vehicle = vehicles.find((item) => item.id === status.vehicle_id);

  const { data: placesData } = useGetAllPlacesQuery();

  const placesOptions = useMemo(() => getPlacesOptionsToSelect(placesData?.items), [placesData]);

  const {
    control,
    handleSubmit,
    formState: { isDirty, isValid },
    trigger,
  } = useForm<FormState>({
    defaultValues: {
      cycleStartedAt: status.timestamp,
      cycleCompletedAt: new Date(new Date(status.timestamp).getTime() + MIN_TRIP_DURATION).toISOString(),
    },
    mode: 'onChange',
  });

  const [createTrip, { isLoading }] = useCreateTripMutation();

  const handleAdd = async (data: FormState) => {
    const { cycleStartedAt, cycleCompletedAt, loadingPlaceId, unloadingPlaceId } = data;

    try {
      await createTrip({
        vehicle_id: status.vehicle_id,
        cycle_started_at: cycleStartedAt,
        cycle_completed_at: cycleCompletedAt,
        loading_place_id: Number(loadingPlaceId),
        unloading_place_id: Number(unloadingPlaceId),
      }).unwrap();

      toast.success({ message: `Добавлен новый рейс для «${vehicle?.name}»` });

      onClose();
    } catch (error: unknown) {
      if (
        typeof error === 'object' &&
        error &&
        'data' in error &&
        typeof error.data === 'object' &&
        error.data &&
        'detail' in error.data &&
        typeof error.data.detail === 'string'
      ) {
        toast.error({ message: error.data.detail });
      } else {
        toast.error({ message: 'Возникла непредвиденная ошибка' });
      }
    }
  };

  const onSubmit = (data: FormState) => {
    void handleAdd(data);
  };

  const disabledSubmitButton = !isDirty || !isValid;

  return (
    <Drawer.Root
      size={620}
      opened={isOpen}
      onClose={onClose}
      position="right"
    >
      <Drawer.Overlay />
      <Drawer.Content>
        <Drawer.Header>
          <Drawer.Title>Новый рейс</Drawer.Title>
          <Drawer.CloseButton />
        </Drawer.Header>
        <Drawer.Body>
          <form
            className={styles.root}
            onSubmit={handleSubmit(onSubmit)}
          >
            <div className={styles.content_container}>
              <div className={styles.inputs_container}>
                <TextInput
                  value={vehicle?.name}
                  label="Наименование техники"
                  readOnly
                  disabled
                />
                <Controller
                  name="cycleStartedAt"
                  control={control}
                  rules={{
                    required: 'Заполните поле',
                    validate: (value, formValues) => dateValidator(value, formValues.cycleCompletedAt),
                  }}
                  render={({ field: { value, onChange, onBlur }, fieldState }) => (
                    <DateTimePicker
                      onBlur={onBlur}
                      value={hasValue(value) ? tz.toTimezone(new Date(value)) : null}
                      onChange={(date) => {
                        onChange(date ? tz.toUTCStringWithSeconds(new Date(date)) : null);
                        void trigger('cycleCompletedAt');
                      }}
                      label="Время начала рейса"
                      error={fieldState.error?.message}
                      withAsterisk
                      minDate={tz.toTimezone(new Date(status.timestamp))}
                      maxDate={
                        nextStatus
                          ? tz.toTimezone(new Date(new Date(nextStatus.timestamp).getTime() - MIN_TRIP_DURATION))
                          : undefined
                      }
                    />
                  )}
                />
                <Controller
                  name="cycleCompletedAt"
                  control={control}
                  rules={{
                    required: 'Заполните поле',
                    validate: (value, formValues) => dateValidator(formValues.cycleStartedAt, value),
                  }}
                  render={({ field: { value, onChange, onBlur }, fieldState }) => (
                    <DateTimePicker
                      onBlur={onBlur}
                      value={hasValue(value) ? tz.toTimezone(new Date(value)) : null}
                      onChange={(date) => {
                        onChange(date ? tz.toUTCStringWithSeconds(new Date(date)) : null);
                        void trigger('cycleStartedAt');
                      }}
                      label="Время окончания рейса"
                      error={fieldState.error?.message}
                      withAsterisk
                      minDate={tz.toTimezone(new Date(new Date(status.timestamp).getTime() + MIN_TRIP_DURATION))}
                    />
                  )}
                />
                <Controller
                  name="loadingPlaceId"
                  control={control}
                  rules={{
                    required: true,
                  }}
                  render={({ field, fieldState }) => (
                    <Select
                      {...field}
                      withAsterisk
                      value={hasValue(field.value) ? String(field.value) : null}
                      data={placesOptions.load}
                      onChange={field.onChange}
                      label="Пункт погрузки"
                      error={fieldState.error?.message}
                    />
                  )}
                />
                <Controller
                  name="unloadingPlaceId"
                  control={control}
                  rules={{
                    required: true,
                  }}
                  render={({ field, fieldState }) => (
                    <Select
                      {...field}
                      withAsterisk
                      value={hasValue(field.value) ? String(field.value) : null}
                      data={placesOptions.unload}
                      onChange={field.onChange}
                      label="Пункт разгрузки"
                      error={fieldState.error?.message}
                    />
                  )}
                />
              </div>
            </div>
            <div>
              <AppButton
                type="submit"
                disabled={disabledSubmitButton}
                loading={isLoading}
                fullWidth
              >
                Сохранить
              </AppButton>
            </div>
          </form>
        </Drawer.Body>
      </Drawer.Content>
    </Drawer.Root>
  );
}

function dateValidator(startDate: string, endDate: string) {
  if (!isValidStatusDurationToAddTrip(startDate, endDate)) {
    return 'Продолжительность рейса должна быть не менее 20 минут';
  }
}

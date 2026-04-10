import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { VEHICLE_TYPES, vehicleTypeOptions, generateVehicleName } from '@/entities/vehicle';

import {
  useCreateEquipmentModelMutation,
  useDeleteEquipmentModelMutation,
  useGetAllEquipmentModelsQuery,
  useUpdateEquipmentModelMutation,
} from '@/shared/api/endpoints/equipment-models';
import {
  type CreateVehicleRequest,
  type UpdateVehicleRequest,
  useCreateVehicleMutation,
  useUpdateVehicleMutation,
  type Vehicle,
} from '@/shared/api/endpoints/vehicles';
import { DEFAULT_ENTERPRISE_ID } from '@/shared/config/constants';
import { useConfirm } from '@/shared/lib/confirm';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { convertToNumberOrNull } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { POSITIVE_NUMBER_VALIDATION, SELECT_VALIDATION, STRING_VALIDATION } from '@/shared/lib/validation';
import { AppButton } from '@/shared/ui/AppButton';
import { toast } from '@/shared/ui/Toast';

import { mapActions } from '../../..';
import { DateField } from '../FormFields/DateField';
import { EditableSelectField } from '../FormFields/EditableSelectField';
import { NumberField } from '../FormFields/NumberField';
import { SelectField } from '../FormFields/SelectField';
import { TextField } from '../FormFields/TextField';
import { FormHeader } from '../FormHeader';

import styles from './Form.module.css';

const ValidationShema = z.object({
  registrationNumber: STRING_VALIDATION,
  vehicleType: z.enum(VEHICLE_TYPES),
  modelId: SELECT_VALIDATION,
  serialNumber: STRING_VALIDATION,
  maxSpeed: POSITIVE_NUMBER_VALIDATION,
  tankVolume: POSITIVE_NUMBER_VALIDATION,
  loadCapacityTons: POSITIVE_NUMBER_VALIDATION,
  volumeBody: POSITIVE_NUMBER_VALIDATION,
  activeFrom: z.string().optional().nullable(),
  activeTo: z.string().optional().nullable(),
});

/** Представляет состояние формы. */
type FormState = z.infer<typeof ValidationShema>;

/**
 * Представляет свойства компонента формы для создания или редактирования транспортных средств.
 */
interface VehicleFormProps {
  /** Возвращает делегат, вызываемый при закрытии. */
  readonly onClose: () => void;
  /** Возвращает редактируемое транспортное средство. */
  readonly vehicle?: Vehicle;
}

/**
 * Представляет компонент формы для создания или редактирования транспортных средств.
 */
export function VehicleForm({ onClose, vehicle }: VehicleFormProps) {
  const confirm = useConfirm();
  const dispatch = useAppDispatch();

  const [createVehicle, { isLoading: isLoadingCreateVehicle }] = useCreateVehicleMutation();
  const [updateVehicle, { isLoading: isLoadingUpdateVehicle }] = useUpdateVehicleMutation();

  const { data: equipmentModelsData = EMPTY_ARRAY } = useGetAllEquipmentModelsQuery();
  const equipmentModels = [...equipmentModelsData].sort((a, b) => a.name.localeCompare(b.name));
  const modelOptions = equipmentModels.map((model) => ({
    value: String(model.id),
    label: model.name,
  }));

  const [createEquipmentModel, { isLoading: isLoadingCreateEquipmentModel }] = useCreateEquipmentModelMutation();
  const [updateEquipmentModel, { isLoading: isLoadingUpdateEquipmentModel }] = useUpdateEquipmentModelMutation();
  const [deleteEquipmentModel, { isLoading: isLoadingDeleteEquipmentModel }] = useDeleteEquipmentModelMutation();

  const handleCreateModel = async (name: string) => {
    const newModel = await createEquipmentModel({ name }).unwrap();
    return {
      value: String(newModel.id),
      label: newModel.name,
      volume_m3: newModel.volume_m3,
      load_capacity_tons: newModel.load_capacity_tons,
      max_speed: newModel.max_speed,
      tank_volume: newModel.tank_volume,
    };
  };

  const handleRenameModel = async (value: string, newName: string) => {
    await updateEquipmentModel({
      id: Number(value),
      body: { name: newName },
    }).unwrap();
  };

  const handleDeleteModel = async (value: string) => {
    const model = equipmentModels.find((m) => m.id === Number(value));
    const modelName = model?.name ?? 'модель';

    const isConfirmed = await confirm({
      title: 'Удаление',
      message: `Вы уверены, что хотите удалить модель: «${modelName}»?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (!isConfirmed) return false;

    await deleteEquipmentModel(Number(value)).unwrap();

    return true;
  };

  const methods = useForm<FormState>({
    mode: 'onChange',
    defaultValues: getFormDefaultValues(vehicle),
    resolver: zodResolver(ValidationShema),
  });

  const {
    handleSubmit,
    control,
    formState: { isDirty, isValid },
    setValue,
    trigger,
    reset,
  } = methods;

  useEffect(() => {
    reset(getFormDefaultValues(vehicle));
  }, [reset, vehicle]);

  useEffect(() => {
    dispatch(mapActions.setHasUnsavedChanges(isDirty));
  }, [dispatch, isDirty]);

  const [minActiveTo, maxActiveFrom] = useWatch({
    control,
    name: ['activeFrom', 'activeTo'],
  });

  const handleChangeModelId = (value: string | null) => {
    const equipmentModel = equipmentModelsData.find((item) => hasValue(value) && item.id === Number(value));

    setValue('maxSpeed', equipmentModel?.max_speed ?? '');
    setValue('tankVolume', equipmentModel?.tank_volume ?? '');
    setValue('loadCapacityTons', equipmentModel?.load_capacity_tons ?? '');
    setValue('volumeBody', equipmentModel?.volume_m3 ?? '');

    void trigger();
  };

  const hasModelFieldsChanged = (modelId: number, formData: FormState) => {
    const existingModel = equipmentModels.find((m) => m.id === modelId);
    if (!existingModel) return false;

    return (
      convertToNumberOrNull(formData.volumeBody) !== existingModel.volume_m3 ||
      convertToNumberOrNull(formData.loadCapacityTons) !== existingModel.load_capacity_tons ||
      convertToNumberOrNull(formData.maxSpeed) !== existingModel.max_speed ||
      convertToNumberOrNull(formData.tankVolume) !== existingModel.tank_volume
    );
  };

  const handleAdd = async (formData: FormState) => {
    const request = async () => {
      const modelId = formData.modelId ?? null;

      // Если изменились поля модели — обновляем её
      if (hasValue(modelId) && hasModelFieldsChanged(Number(modelId), formData)) {
        await updateEquipmentModel({
          id: Number(modelId),
          body: {
            volume_m3: convertToNumberOrNull(formData.volumeBody),
            load_capacity_tons: convertToNumberOrNull(formData.loadCapacityTons),
            max_speed: convertToNumberOrNull(formData.maxSpeed),
            tank_volume: convertToNumberOrNull(formData.tankVolume),
          },
        }).unwrap();
      }

      const vehicleData: CreateVehicleRequest = {
        enterprise_id: DEFAULT_ENTERPRISE_ID,
        vehicle_type: formData.vehicleType,
        name: generateVehicleName(formData.vehicleType, formData.registrationNumber),
        model_id: Number(modelId),
        serial_number: formData.serialNumber,
        registration_number: formData.registrationNumber,
        active_from: formData.activeFrom || null,
        active_to: formData.activeTo || null,
      };

      await createVehicle(vehicleData).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Добавление объекта' },
      success: { message: 'Объект добавлен' },
      error: { message: 'Ошибка добавления' },
    });
  };

  const handleEdit = async (id: string | number, formData: FormState) => {
    const request = async () => {
      const modelId = formData.modelId ?? null;

      // Если изменились поля модели — обновляем её
      if (hasValue(modelId) && hasModelFieldsChanged(Number(modelId), formData)) {
        await updateEquipmentModel({
          id: Number(modelId),
          body: {
            volume_m3: convertToNumberOrNull(formData.volumeBody),
            load_capacity_tons: convertToNumberOrNull(formData.loadCapacityTons),
            max_speed: convertToNumberOrNull(formData.maxSpeed),
            tank_volume: convertToNumberOrNull(formData.tankVolume),
          },
        }).unwrap();
      }

      const vehicleData: UpdateVehicleRequest = {
        vehicle_type: formData.vehicleType,
        name: generateVehicleName(formData.vehicleType, formData.registrationNumber),
        model_id: Number(modelId),
        serial_number: formData.serialNumber,
        registration_number: formData.registrationNumber,
        active_from: formData.activeFrom || null,
        active_to: formData.activeTo || null,
      };

      await updateVehicle({ id: Number(id), body: vehicleData }).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Сохранение изменений' },
      success: { message: 'Изменения сохранены' },
      error: { message: 'Ошибка сохранения' },
    });
  };

  const onSubmit = async (data: FormState) => {
    if (vehicle) {
      await handleEdit(vehicle.id, data);
    } else {
      await handleAdd(data);
    }

    dispatch(mapActions.setFormTarget(null));
    dispatch(mapActions.setHasUnsavedChanges(false));
  };

  const isLoading =
    isLoadingCreateVehicle ||
    isLoadingUpdateVehicle ||
    isLoadingCreateEquipmentModel ||
    isLoadingUpdateEquipmentModel ||
    isLoadingDeleteEquipmentModel;

  const disabledSubmitButton = !isDirty || !isValid;

  return (
    <>
      <FormHeader
        title={vehicle?.name ?? 'Новый объект'}
        onClose={onClose}
      />
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit(onSubmit)}
          className={styles.form}
        >
          <div className={styles.inputs_container}>
            <TextField
              name="registrationNumber"
              label="Гаражный номер"
              required
              disabled={isLoading}
            />
            <SelectField
              name="vehicleType"
              label="Тип"
              required
              options={vehicleTypeOptions}
              disabled={isLoading}
            />
            <EditableSelectField
              name="modelId"
              label="Модель"
              required
              options={modelOptions}
              handlers={{ onCreate: handleCreateModel, onEdit: handleRenameModel, onDelete: handleDeleteModel }}
              onChange={handleChangeModelId}
              disabled={isLoading}
            />
            <TextField
              name="serialNumber"
              label="Идентификатор/номер"
              required
              disabled={isLoading}
            />
            <NumberField
              name="volumeBody"
              label="Объем кузова/ковша, м³"
              required
              disabled={isLoading}
            />
            <NumberField
              name="loadCapacityTons"
              label="Грузоподъемность, т."
              required
              disabled={isLoading}
            />
            <NumberField
              name="maxSpeed"
              label="Макс. скорость, км/ч"
              required
              disabled={isLoading}
            />
            <NumberField
              name="tankVolume"
              label="Объём бака, л."
              required
              disabled={isLoading}
            />
            <DateField
              name="activeFrom"
              label="Дата ввода в эксплуатацию"
              maxDate={maxActiveFrom}
              disabled={isLoading}
            />
            <DateField
              name="activeTo"
              label="Дата вывода из эксплуатации"
              minDate={minActiveTo}
              disabled={isLoading}
            />
          </div>
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

/** Возвращает начальные значения формы. */
function getFormDefaultValues(vehicle?: Vehicle) {
  if (!vehicle) {
    return {
      registrationNumber: '',
      vehicleType: VEHICLE_TYPES.at(0),
      modelId: '',
      serialNumber: '',
      maxSpeed: '',
      tankVolume: '',
      loadCapacityTons: '',
      volumeBody: '',
      activeFrom: undefined,
      activeTo: undefined,
    };
  }

  return {
    registrationNumber: vehicle.registration_number ?? '',
    vehicleType: vehicle.vehicle_type ?? '',
    modelId: vehicle.model_id ?? '',
    serialNumber: vehicle.serial_number ?? '',
    maxSpeed: vehicle.model?.max_speed ?? '',
    tankVolume: vehicle.model?.tank_volume ?? '',
    loadCapacityTons: vehicle.model?.load_capacity_tons ?? '',
    volumeBody: vehicle.model?.volume_m3 ?? '',
    activeFrom: vehicle.active_from ?? undefined,
    activeTo: vehicle.active_to ?? undefined,
  };
}

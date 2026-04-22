import { useMemo } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { generateVehicleName } from '@/entities/vehicle';

import {
  useCreateEquipmentModelMutation,
  useDeleteEquipmentModelMutation,
  useGetAllEquipmentModelsQuery,
  useUpdateEquipmentModelMutation,
  type EquipmentModelSpecs,
} from '@/shared/api/endpoints/equipment-models';
import {
  useCreateVehicleMutation,
  useDeleteVehicleMutation,
  useGetVehiclesInfiniteQuery,
  useUpdateVehicleMutation,
} from '@/shared/api/endpoints/vehicles';
import type { CreateVehicleRequest, UpdateVehicleRequest, Vehicle } from '@/shared/api/endpoints/vehicles';
import { DEFAULT_ENTERPRISE_ID } from '@/shared/config/constants';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { useConfirm } from '@/shared/lib/confirm';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { getBaseColumns } from '../../model/equipment-columns';

/**
 * Тип данных формы оборудования с полями связанной сущности (модели).
 * Имена полей соответствуют `accessorKey` в `columns.ts` и API.
 */
type VehicleFormData = Partial<Vehicle> & Partial<EquipmentModelSpecs>;

/**
 * Представляет компонент страницы справочника «Оборудование».
 */
export function EquipmentPage() {
  const confirm = useConfirm();

  const {
    data: vehiclesData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch: refetchVehicles,
  } = useGetVehiclesInfiniteQuery({ enterprise_id: DEFAULT_ENTERPRISE_ID });
  const vehicles = useMemo(() => {
    return vehiclesData?.pages.flatMap((page) => page.items) ?? [];
  }, [vehiclesData]);
  const total = vehiclesData?.pages[0]?.total ?? 0;

  const [createVehicle] = useCreateVehicleMutation();
  const [updateVehicle] = useUpdateVehicleMutation();
  const [deleteVehicle] = useDeleteVehicleMutation();

  const { data: equipmentModelsData = EMPTY_ARRAY } = useGetAllEquipmentModelsQuery();
  const equipmentModels = [...equipmentModelsData].sort((a, b) => a.name.localeCompare(b.name));

  const [createEquipmentModel] = useCreateEquipmentModelMutation();
  const [updateEquipmentModel] = useUpdateEquipmentModelMutation();
  const [deleteEquipmentModel] = useDeleteEquipmentModelMutation();

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

    void refetchVehicles();
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

    void refetchVehicles();
    return true;
  };

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      void fetchNextPage();
    }
  };

  const columns = getBaseColumns({
    equipmentModels,
    modelHandlers: {
      onCreate: handleCreateModel,
      onEdit: handleRenameModel,
      onDelete: handleDeleteModel,
    },
  });

  // Проверяет, изменились ли поля модели
  const hasModelFieldsChanged = (modelId: number, formData: VehicleFormData) => {
    const existingModel = equipmentModels.find((m) => m.id === modelId);
    if (!existingModel) return false;

    return (
      formData.volume_m3 !== existingModel.volume_m3 ||
      formData.load_capacity_tons !== existingModel.load_capacity_tons ||
      formData.max_speed !== existingModel.max_speed ||
      formData.tank_volume !== existingModel.tank_volume
    );
  };

  const handleAdd = async (formData: VehicleFormData) => {
    const request = async () => {
      const modelId = formData.model_id ?? null;

      // Если изменились поля модели — обновляем её
      if (hasValue(modelId) && hasModelFieldsChanged(modelId, formData)) {
        await updateEquipmentModel({
          id: modelId,
          body: {
            volume_m3: formData.volume_m3 ?? null,
            load_capacity_tons: formData.load_capacity_tons ?? null,
            max_speed: formData.max_speed ?? null,
            tank_volume: formData.tank_volume ?? null,
          },
        }).unwrap();
      }

      assertHasValue(formData.vehicle_type);

      const vehicleData: CreateVehicleRequest = {
        enterprise_id: DEFAULT_ENTERPRISE_ID,
        vehicle_type: formData.vehicle_type,
        name: generateVehicleName(formData.vehicle_type, formData.registration_number),
        model_id: modelId,
        serial_number: formData.serial_number || null,
        registration_number: formData.registration_number || null,
        active_from: formData.active_from || null,
        active_to: formData.active_to || null,
      };

      await createVehicle(vehicleData).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Добавление объекта' },
      success: { message: 'Объект добавлен в таблицу' },
      error: { message: 'Ошибка добавления' },
    });
  };

  const handleEdit = async (id: string | number, formData: VehicleFormData) => {
    const request = async () => {
      const modelId = formData.model_id ?? null;

      // Если изменились поля модели — обновляем её
      if (hasValue(modelId) && hasModelFieldsChanged(modelId, formData)) {
        await updateEquipmentModel({
          id: modelId,
          body: {
            volume_m3: formData.volume_m3 ?? null,
            load_capacity_tons: formData.load_capacity_tons ?? null,
            max_speed: formData.max_speed ?? null,
            tank_volume: formData.tank_volume ?? null,
          },
        }).unwrap();
      }

      const vehicleData: UpdateVehicleRequest = {
        vehicle_type: formData.vehicle_type,
        name: formData.vehicle_type
          ? generateVehicleName(formData.vehicle_type, formData.registration_number)
          : formData.name,
        model_id: modelId,
        serial_number: formData.serial_number || null,
        registration_number: formData.registration_number || null,
        active_from: formData.active_from || null,
        active_to: formData.active_to || null,
      };

      await updateVehicle({ id: Number(id), body: vehicleData }).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Сохранение изменений' },
      success: { message: 'Изменения сохранены' },
      error: { message: 'Ошибка сохранения' },
    });
  };

  const handleDelete = async (ids: (string | number)[]) => {
    await Promise.all(ids.map((id) => deleteVehicle(Number(id)).unwrap()));
  };

  return (
    <Page variant="table">
      <TableProvider
        data={vehicles}
        columns={columns}
        total={total}
        storageKey="asu-gtk-equipment"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.EQUIPMENT}
        >
          <ControlPanel />
        </Header>

        <div className="table-wrapper">
          <Table
            data={vehicles}
            columns={columns}
            isLoading={isLoading || (isFetching && vehicles.length > 0)}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

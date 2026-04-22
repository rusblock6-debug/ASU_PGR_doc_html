import { Header, Page } from '@/widgets/page-layout';

import {
  useCreateLoadTypeCategoryMutation,
  useDeleteLoadTypeCategoryMutation,
  useGetAllLoadTypeCategoriesQuery,
  useUpdateLoadTypeCategoryMutation,
} from '@/shared/api/endpoints/load-type-categories';
import {
  useCreateLoadTypeMutation,
  useDeleteLoadTypeMutation,
  useGetLoadTypesInfiniteQuery,
  useUpdateLoadTypeMutation,
} from '@/shared/api/endpoints/load-types';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { useConfirm } from '@/shared/lib/confirm';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { cargoColumns, type CargoTableData, transformCargoToTableData } from '../../model/cargo-columns';

/** Представляет компонент страницы справочника «Виды груза». */
export function CargoPage() {
  const confirm = useConfirm();

  const { data: cargoCategoriesData = EMPTY_ARRAY } = useGetAllLoadTypeCategoriesQuery();
  const cargoCategories = [...cargoCategoriesData].sort((a, b) => a.name.localeCompare(b.name));

  const [createCargoCategory] = useCreateLoadTypeCategoryMutation();
  const [updateCargoCategory] = useUpdateLoadTypeCategoryMutation();
  const [deleteCargoCategory] = useDeleteLoadTypeCategoryMutation();

  const {
    data: cargoesData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch: refetchCargoes,
  } = useGetLoadTypesInfiniteQuery();

  const [createCargo] = useCreateLoadTypeMutation();
  const [updateCargo] = useUpdateLoadTypeMutation();
  const [deleteCargo] = useDeleteLoadTypeMutation();

  const cargoes = cargoesData?.pages.flatMap((page) => page.items.map(transformCargoToTableData)) ?? EMPTY_ARRAY;
  const total = cargoesData?.pages[0]?.total ?? 0;

  const handleCreateCategory = async (name: string) => {
    const category = await createCargoCategory({ name }).unwrap();
    return {
      value: String(category.id),
      label: category.name,
    };
  };

  const handleRenameCategory = async (value: string, newName: string) => {
    await updateCargoCategory({
      id: Number(value),
      body: { name: newName },
    }).unwrap();

    refetchCargoes();
  };

  const handleDeleteCategory = async (value: string) => {
    const category = cargoCategories.find((m) => m.id === Number(value));
    const categoryName = category?.name ?? 'неизвестная категория';

    const isConfirmed = await confirm({
      title: 'Удаление',
      message: `Вы уверены, что хотите удалить категорию вида груза: «${categoryName}»?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (!isConfirmed) return false;

    await deleteCargoCategory(Number(value)).unwrap();

    refetchCargoes();
    return true;
  };

  const columns = cargoColumns({
    cargoCategories,
    cargoCategoriesHandlers: {
      onCreate: handleCreateCategory,
      onEdit: handleRenameCategory,
      onDelete: handleDeleteCategory,
    },
  });

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      fetchNextPage();
    }
  };

  const prepareCargoData = async (formData: Partial<CargoTableData>) => {
    const { name, color, density, category_id: categoryId } = formData;

    const category = cargoCategories.find((m) => m.id === categoryId);
    if (!category) return null;

    assertHasValue(name);
    assertHasValue(color);
    assertHasValue(density);
    assertHasValue(categoryId);
    assertHasValue(category.name);

    const hasCategoryChanged = formData.is_mineral !== category.is_mineral;

    if (hasCategoryChanged) {
      await updateCargoCategory({
        id: categoryId,
        body: {
          name: category.name,
          is_mineral: formData.is_mineral,
        },
      }).unwrap();
    }

    return { name, color, density, category_id: categoryId };
  };

  const handleAdd = async (formData: Partial<CargoTableData>) => {
    const request = async () => {
      const cargoData = await prepareCargoData(formData);
      if (!cargoData) return;

      await createCargo(cargoData).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Создание вида груза' },
      success: { message: 'Новый вид груза добавлен в таблицу' },
      error: { message: 'Ошибка добавления' },
    });
  };

  const handleEdit = async (id: number | string, formData: Partial<CargoTableData>) => {
    const request = async () => {
      const cargoData = await prepareCargoData(formData);
      if (!cargoData) return;

      await updateCargo({ id: Number(id), body: cargoData }).unwrap();
    };

    await toast.promise(request(), {
      loading: { message: 'Сохранение изменений' },
      success: { message: 'Изменения сохранены' },
      error: { message: 'Ошибка сохранения' },
    });
  };

  const handleDelete = async (ids: (string | number)[]) => {
    await Promise.all(ids.map((id) => deleteCargo(Number(id)).unwrap()));
  };

  return (
    <Page variant="table">
      <TableProvider
        data={cargoes}
        columns={columns}
        total={total}
        storageKey="asu-gtk-cargo"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.CARGO}
        >
          <ControlPanel />
        </Header>

        <div className="table-wrapper">
          <Table
            data={cargoes}
            columns={columns}
            isLoading={isLoading || isFetching}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

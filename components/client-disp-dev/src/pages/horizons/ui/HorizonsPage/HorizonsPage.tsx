import { useMemo } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import {
  type Horizon,
  useCreateHorizonMutation,
  useDeleteHorizonMutation,
  useGetHorizonsInfiniteQuery,
  useUpdateHorizonMutation,
} from '@/shared/api/endpoints/horizons';
import {
  useCreateShaftMutation,
  useDeleteShaftMutation,
  useGetAllShaftsQuery,
  useUpdateShaftMutation,
} from '@/shared/api/endpoints/shafts';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { useConfirm } from '@/shared/lib/confirm';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { getColumns } from '../../model/columns';

/**
 * Представляет компонент страницы-справочника "Горизонты".
 */
export function HorizonsPage() {
  const confirm = useConfirm();

  const {
    data: horizonsData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetHorizonsInfiniteQuery();

  const [createHorizon] = useCreateHorizonMutation();
  const [updateHorizon] = useUpdateHorizonMutation();
  const [deleteHorizon] = useDeleteHorizonMutation();

  const { data: shaftsData, isLoading: isLoadingShafts, isFetching: isFetchingShafts } = useGetAllShaftsQuery();

  const [createShaft] = useCreateShaftMutation();
  const [updateShaft] = useUpdateShaftMutation();
  const [deleteShaft] = useDeleteShaftMutation();

  const shaftsOptions = useMemo(() => {
    if (shaftsData) {
      return shaftsData.items.map((item) => ({
        value: String(item.id),
        label: item.name,
      }));
    }
    return EMPTY_ARRAY;
  }, [shaftsData]);

  const horizons = useMemo(() => {
    return horizonsData?.pages.flatMap((page) => page.items) ?? EMPTY_ARRAY;
  }, [horizonsData]);

  const total = horizonsData?.pages[0]?.total ?? 0;

  const handleCreateShaft = async (name: string) => {
    const newModel = await createShaft({ name }).unwrap();
    return {
      value: String(newModel.id),
      label: newModel.name,
    };
  };

  const handleRenameShaft = async (value: string, newName: string) => {
    await updateShaft({ id: Number(value), body: { name: newName } }).unwrap();
  };

  const handleDeleteShaft = async (value: string) => {
    const model = shaftsData?.items.find((shaft) => shaft.id === Number(value));
    const modelName = model?.name ?? 'шахта';

    const isConfirmed = await confirm({
      title: 'Удаление',
      message: `Вы уверены, что хотите удалить шахту: «${modelName}»?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (!isConfirmed) return false;

    await deleteShaft(Number(value)).unwrap();
    return true;
  };

  const columns = getColumns({
    selectOptions: [...shaftsOptions],
    handlers: {
      onCreate: handleCreateShaft,
      onEdit: handleRenameShaft,
      onDelete: handleDeleteShaft,
    },
  });

  const handleAdd = async (newHorizon: Partial<Horizon>) => {
    const { name, height, shafts } = newHorizon;
    assertHasValue(name);
    assertHasValue(height);

    const request = createHorizon({
      ...newHorizon,
      name,
      height,
      shafts: shafts?.map((item) => Number(item)),
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление нового горизонта «${name}»`,
      },
      success: {
        message: `Добавлен новый горизонт «${name}»`,
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  const handleEdit = async (id: number | string, updatedData: Partial<Horizon>) => {
    const { shafts, ...data } = updatedData;

    await updateHorizon({
      horizonId: Number(id),
      body: { ...data, shafts: shafts?.map((item) => Number(item)) },
    }).unwrap();
  };

  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deleteHorizon(Number(id)).unwrap()));
  };

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      fetchNextPage();
    }
  };

  return (
    <Page variant="table">
      <TableProvider
        data={horizons}
        columns={columns}
        total={total}
        storageKey="asu-gtk-horizons"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.HORIZONS}
        >
          <ControlPanel />
        </Header>
        <div className="table-wrapper">
          <Table
            data={horizons}
            columns={columns}
            isLoading={isLoading || isFetching || isFetchingShafts || isLoadingShafts}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

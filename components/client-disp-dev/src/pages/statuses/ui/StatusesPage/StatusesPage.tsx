import { useMemo } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { useGetAllAnalyticCategoriesQuery } from '@/shared/api/endpoints/analytic-categories';
import {
  useCreateOrganizationCategoryMutation,
  useDeleteOrganizationCategoryMutation,
  useGetAllOrganizationCategoriesQuery,
  useUpdateOrganizationCategoryMutation,
} from '@/shared/api/endpoints/organization-categories';
import {
  type Status,
  useCreateStatusMutation,
  useDeleteStatusMutation,
  useGetStatusesInfiniteQuery,
  useUpdateStatusMutation,
} from '@/shared/api/endpoints/statuses';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { useConfirm } from '@/shared/lib/confirm';
import { hasValue } from '@/shared/lib/has-value';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { statusesColumns } from '../../model/statuses-columns';

/**
 * Представляет компонент страницы-справочника "Статусы".
 */
export function StatusesPage() {
  const confirm = useConfirm();

  const { data: organizationCategoriesData } = useGetAllOrganizationCategoriesQuery();

  const [createOrganizationCategory] = useCreateOrganizationCategoryMutation();
  const [updateOrganizationCategory] = useUpdateOrganizationCategoryMutation();
  const [deleteOrganizationCategory] = useDeleteOrganizationCategoryMutation();

  const handleCreateOrganizationCategory = async (name: string) => {
    const newModel = await createOrganizationCategory({ name }).unwrap();
    return {
      value: String(newModel.id),
      label: newModel.name,
    };
  };

  const handleRenameOrganizationCategory = async (value: string, newName: string) => {
    await updateOrganizationCategory({ organizationCategoryId: Number(value), body: { name: newName } }).unwrap();
    void refetchStatuses();
  };

  const handleDeleteOrganizationCategory = async (value: string) => {
    const model = organizationCategoriesData?.items.find((shaft) => shaft.id === Number(value));
    const modelName = model?.name ?? 'статус';

    const isConfirmed = await confirm({
      title: 'Удаление',
      message: `Вы уверены, что хотите удалить статус организационной категории: «${modelName}»?`,
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    });

    if (!isConfirmed) return false;

    await deleteOrganizationCategory(Number(value)).unwrap();
    void refetchStatuses();
    return true;
  };

  const { data: analyticCategoriesData } = useGetAllAnalyticCategoriesQuery();

  const {
    data: statusesData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch: refetchStatuses,
  } = useGetStatusesInfiniteQuery();

  const [createStatus] = useCreateStatusMutation();
  const [updateStatus] = useUpdateStatusMutation();
  const [deleteStatus] = useDeleteStatusMutation();

  const statuses = useMemo(() => {
    return statusesData?.pages.flatMap((page) => page.items) ?? [];
  }, [statusesData]);

  const total = statusesData?.pages[0]?.total ?? 0;

  const organizationCategoryOptions = useMemo(() => {
    if (organizationCategoriesData) {
      return Array.from(organizationCategoriesData.items)
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((item) => ({
          value: String(item.id),
          label: item.name,
        }));
    }
    return [];
  }, [organizationCategoriesData]);

  const analyticCategoryOptions = useMemo(() => {
    if (analyticCategoriesData) {
      return Array.from(analyticCategoriesData)
        .sort((a, b) => a.display_name.localeCompare(b.display_name))
        .map((item) => ({
          value: item.value,
          label: item.display_name,
        }));
    }
    return [];
  }, [analyticCategoriesData]);

  const columns = statusesColumns(
    {
      selectOptions: organizationCategoryOptions,
      handlers: {
        onCreate: handleCreateOrganizationCategory,
        onEdit: handleRenameOrganizationCategory,
        onDelete: handleDeleteOrganizationCategory,
      },
    },
    analyticCategoryOptions,
  );

  const handleAdd = async (newStatus: Partial<Status>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { display_name, color, organization_category_id, ...status } = newStatus;
    assertHasValue(display_name);
    assertHasValue(color);

    const request = createStatus({
      ...status,
      display_name,
      color,
      organization_category_id: hasValue(organization_category_id) ? organization_category_id : undefined,
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление нового статуса «${newStatus.display_name}»`,
      },
      success: {
        message: `Добавлен новый статус «${newStatus.display_name}»`,
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  const handleEdit = async (id: number | string, updatedData: Partial<Status>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { organization_category_id, ...status } = updatedData;

    const editingStatus = statuses.find((item) => item.id === id);

    if (status.is_work_status !== editingStatus?.is_work_status && editingStatus?.system_status) {
      throw new Error(
        'Для системных статусов отсутствует возможность изменять значение поля "Является рабочим статусом".',
      );
    }

    await updateStatus({
      statusId: Number(id),
      body: {
        ...status,
        organization_category_id: hasValue(organization_category_id) ? organization_category_id : undefined,
      },
    }).unwrap();
  };

  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deleteStatus(Number(id)).unwrap()));
  };

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      void fetchNextPage();
    }
  };

  return (
    <Page variant="table">
      <TableProvider
        data={statuses}
        columns={columns}
        total={total}
        storageKey="asu-gtk-statuses"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.STATUSES}
        >
          <ControlPanel />
        </Header>
        <div className="table-wrapper">
          <Table
            data={statuses}
            columns={columns}
            isLoading={isLoading || isFetching}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

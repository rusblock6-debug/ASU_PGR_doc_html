import { useMemo } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { useGetAllRolesQuery } from '@/shared/api/endpoints/roles';
import {
  type Staff,
  useGetStaffInfiniteQuery,
  useCreateStaffMutation,
  useDeleteStaffMutation,
  useUpdateStaffMutation,
  useGetStaffPositionsQuery,
  useGetStaffDepartmentsQuery,
} from '@/shared/api/endpoints/staff';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { getColumns } from '../../model/columns';

/**
 * Представляет компонент страницы "Персонал".
 */
export function StaffPage() {
  const {
    data: staffData,
    isLoading: isLoadingStaffData,
    isFetching: isFetchingStaffData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetStaffInfiniteQuery();

  const { data: rolesData, isLoading: isLoadingRolesData, isFetching: isFetchingRolesData } = useGetAllRolesQuery();
  const {
    data: positionsData,
    isLoading: isLoadingPositionsData,
    isFetching: isFetchingPositionsData,
  } = useGetStaffPositionsQuery();
  const {
    data: departmentsData,
    isLoading: isLoadingDepartmentsData,
    isFetching: isFetchingDepartmentsData,
  } = useGetStaffDepartmentsQuery();

  const [createRole] = useCreateStaffMutation();
  const [updateRole] = useUpdateStaffMutation();
  const [deleteRole] = useDeleteStaffMutation();

  const staff = useMemo(() => staffData?.pages.flatMap((page) => page.items) ?? [], [staffData]);

  const rolesSelectorOptions = useMemo(
    () => rolesData?.items.map((item) => ({ value: String(item.id), label: item.name })) ?? [],
    [rolesData],
  );

  const staffPositions = useMemo(() => positionsData?.items ?? EMPTY_ARRAY, [positionsData]);
  const staffDepartments = useMemo(() => departmentsData?.items ?? EMPTY_ARRAY, [departmentsData]);

  const columns = getColumns(rolesSelectorOptions, staffPositions, staffDepartments);
  const total = staffData?.pages[0]?.total ?? 0;
  const isTableDataLoading =
    isLoadingStaffData ||
    isFetchingStaffData ||
    isLoadingRolesData ||
    isFetchingRolesData ||
    isLoadingPositionsData ||
    isFetchingPositionsData ||
    isLoadingDepartmentsData ||
    isFetchingDepartmentsData;

  const handleAdd = async (newStaff: Partial<Staff>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { name, surname, personnel_number, username, role_id, password, ...data } = newStaff;
    assertHasValue(name);
    assertHasValue(surname);
    assertHasValue(username);
    assertHasValue(password);
    assertHasValue(personnel_number);
    assertHasValue(role_id);

    const request = createRole({
      name,
      surname,
      username,
      password,
      role_id,
      personnel_number,
      ...data,
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление нового сотрудника ${surname} ${name}${data.patronymic ? ' ' + data.patronymic : ''}.`,
      },
      success: {
        message: `Добавлен новый сотрудник ${surname} ${name}${data.patronymic ? ' ' + data.patronymic : ''}.`,
      },
      error: {
        message: 'Ошибка добавления.',
      },
    });
  };

  const handleEdit = async (id: number | string, data: Partial<Staff>) => {
    await updateRole({
      id: Number(id),
      body: data,
    }).unwrap();
  };

  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deleteRole(Number(id)).unwrap()));
  };

  const handleScrollToBottom = () => {
    if (!isFetchingStaffData && !isFetchingNextPage && hasNextPage) {
      void fetchNextPage();
    }
  };

  return (
    <Page variant="table">
      <TableProvider
        data={staff}
        columns={columns}
        total={total}
        storageKey="asu-gtk-staff"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.staff_id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.STAFF}
        >
          <ControlPanel />
        </Header>
        <div className="table-wrapper">
          <Table
            data={staff}
            columns={columns}
            isLoading={isTableDataLoading}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

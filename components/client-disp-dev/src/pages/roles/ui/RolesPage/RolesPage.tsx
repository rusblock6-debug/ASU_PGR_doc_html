import { useMemo, useState } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { type Role, useGetRolesInfiniteQuery, useDeleteRoleMutation } from '@/shared/api/endpoints/roles';
import CopyIcon from '@/shared/assets/icons/ic-copy.svg?react';
import { AppRoutes } from '@/shared/routes/router';
import { AppButton } from '@/shared/ui/AppButton';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';

import { getColumns } from '../../model/columns';
import { type DrawerMode, TableDrawer } from '../TableDrawer';

/**
 * Представляет компонент страницы "Роли".
 */
export function RolesPage() {
  const { data: rolesData, isLoading, isFetching } = useGetRolesInfiniteQuery();

  const [deleteRole] = useDeleteRoleMutation();

  const roles = useMemo(() => rolesData?.pages.flatMap((page) => page.items) ?? [], [rolesData]);

  const columns = getColumns();
  const total = rolesData?.pages[0]?.total ?? 0;
  const isTableDataLoading = isLoading || isFetching;

  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deleteRole(Number(id)).unwrap()));
  };

  const [drawerMode, setDrawerMode] = useState<DrawerMode>('closed');
  const [editingRow, setEditingRow] = useState<Role | null>(null);
  const [selectedRow, setSelectedRow] = useState<Role | null>(null);

  const onAddMode = () => {
    setDrawerMode('add');
    setEditingRow(null);
  };

  const onEditMode = (row: Role) => {
    setDrawerMode('edit');
    setEditingRow(row);
  };

  const onCopyMode = () => {
    setDrawerMode('add');
    setEditingRow(selectedRow);
  };

  const onSelectRow = (rows: readonly Role[]) => {
    if (rows.length === 1) {
      setSelectedRow(rows[0]);
    } else {
      setSelectedRow(null);
    }
  };

  const onCloseDrawer = () => {
    setDrawerMode('closed');
    setEditingRow(null);
  };

  return (
    <Page variant="table">
      <TableProvider
        data={roles}
        columns={columns}
        total={total}
        storageKey="asu-gtk-roles"
        onDelete={handleDelete}
        getRowId={(row) => row.id}
        onAddMode={onAddMode}
        onEditMode={onEditMode}
        onCloseDrawer={onCloseDrawer}
        onSelectRow={onSelectRow}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.ROLES}
        >
          <ControlPanel
            centerContent={
              selectedRow && (
                <AppButton
                  variant="clear"
                  size="xs"
                  onClick={onCopyMode}
                  leftSection={<CopyIcon />}
                >
                  Копировать роль
                </AppButton>
              )
            }
          />
        </Header>
        <div className="table-wrapper">
          <Table
            data={roles}
            columns={columns}
            isLoading={isTableDataLoading}
            customDrawer={
              <TableDrawer
                drawerMode={drawerMode}
                onClose={onCloseDrawer}
                role={editingRow}
              />
            }
          />
        </div>
      </TableProvider>
    </Page>
  );
}

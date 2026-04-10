import { useMemo } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import {
  type Section,
  useCreateSectionMutation,
  useDeleteSectionMutation,
  useGetSectionsInfiniteQuery,
  useUpdateSectionMutation,
} from '@/shared/api/endpoints/sections';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { getColumns } from '../../model/columns';

/**
 * Представляет компонент страницы "Участки".
 */
export function SectionsPage() {
  const {
    data: sectionData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetSectionsInfiniteQuery();

  const { data: horizonsData } = useGetAllHorizonsQuery();

  const [createSection] = useCreateSectionMutation();
  const [updateSection] = useUpdateSectionMutation();
  const [deleteSection] = useDeleteSectionMutation();

  const sections = useMemo(() => {
    return sectionData?.pages.flatMap((page) => page.items) ?? EMPTY_ARRAY;
  }, [sectionData]);

  const total = sectionData?.pages.at(0)?.total ?? 0;

  const horizonsSelectorOptions = useMemo(() => {
    return horizonsData?.items.map((item) => ({ value: String(item.id), label: item.name })) ?? EMPTY_ARRAY;
  }, [horizonsData]);

  const columns = getColumns([...horizonsSelectorOptions]);

  const handleAdd = async (newSection: Partial<Section>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { name, is_contractor_organization, horizons } = newSection;
    assertHasValue(name);
    assertHasValue(is_contractor_organization);
    assertHasValue(horizons);

    const request = createSection({
      name,
      is_contractor_organization,
      horizons: horizons.map((item) => Number(item)) ?? EMPTY_ARRAY,
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление нового участка «${name}»`,
      },
      success: {
        message: `Добавлен новый участок «${name}»`,
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  const handleEdit = async (id: number | string, updatedData: Partial<Section>) => {
    await updateSection({
      sectionId: Number(id),
      body: {
        ...updatedData,
        horizons: updatedData.horizons?.map((item) => Number(item)) ?? EMPTY_ARRAY,
      },
    }).unwrap();
  };

  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deleteSection(Number(id)).unwrap()));
  };

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      fetchNextPage();
    }
  };

  return (
    <Page variant="table">
      <TableProvider
        data={sections}
        columns={columns}
        total={total}
        storageKey="asu-gtk-sections"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.SECTIONS}
        >
          <ControlPanel />
        </Header>
        <div className="table-wrapper">
          <Table
            data={sections}
            columns={columns}
            isLoading={isLoading || isFetching}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

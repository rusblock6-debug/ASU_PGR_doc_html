import { Header, Page } from '@/widgets/page-layout';

import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import {
  type CreateTagRequest,
  type UpdateTagRequest,
  useCreateTagMutation,
  useDeleteTagMutation,
  useGetTagsInfiniteQuery,
  useUpdateTagMutation,
} from '@/shared/api/endpoints/tags';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { AppRoutes } from '@/shared/routes/router';
import { ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { tagsColumns, type TagTableData, transformTagToTableData } from '../../model/tags-columns';

/** Представляет компонент страницы справочника «Метки». */
export function TagsPage() {
  const { data: placesData } = useGetAllPlacesQuery();
  const places = placesData?.items?.length ? placesData.items : EMPTY_ARRAY;

  const {
    data: tagsData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetTagsInfiniteQuery();

  const [createTag] = useCreateTagMutation();
  const [updateTag] = useUpdateTagMutation();
  const [deleteTag] = useDeleteTagMutation();

  const tags = tagsData?.pages.flatMap((page) => page.items.map(transformTagToTableData)) ?? EMPTY_ARRAY;
  const total = tagsData?.pages[0]?.total ?? 0;

  const columns = tagsColumns(places);

  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      fetchNextPage();
    }
  };

  const handleAdd = async (formData: Partial<TagTableData>) => {
    const tagName = formData.tag_name;
    const tagMac = formData.tag_mac;

    assertHasValue(tagName);
    assertHasValue(tagMac);

    const request: CreateTagRequest = {
      tag_name: tagName,
      tag_mac: tagMac,
      place_id: hasValue(formData.place_id) ? formData.place_id : null,
    };

    const promise = createTag(request).unwrap();

    await toast.promise(promise, {
      loading: { message: `Добавление новой метки «${tagName}»` },
      success: { message: `Добавлена новая метка «${tagName}»` },
      error: { message: 'Ошибка добавления' },
    });
  };

  const handleEdit = async (id: number | string, formData: Partial<TagTableData>) => {
    const tagName = formData.tag_name;
    const tagMac = formData.tag_mac;

    assertHasValue(tagName);
    assertHasValue(tagMac);

    const body: UpdateTagRequest = {
      tag_name: tagName,
      tag_mac: tagMac,
      place_id: hasValue(formData.place_id) ? formData.place_id : null,
    };

    await updateTag({ id: Number(id), body }).unwrap();
  };

  const handleDelete = async (ids: (string | number)[]) => {
    await Promise.all(ids.map((id) => deleteTag(Number(id)).unwrap()));
  };

  return (
    <Page variant="table">
      <TableProvider
        data={tags}
        columns={columns}
        total={total}
        storageKey="asu-gtk-tags"
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.TAGS}
        >
          <ControlPanel />
        </Header>

        <div className="table-wrapper">
          <Table
            data={tags}
            columns={columns}
            isLoading={isLoading || isFetching}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

import { useMemo, useState } from 'react';

import { Header, Page } from '@/widgets/page-layout';

import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import { useGetAllLoadTypeQuery } from '@/shared/api/endpoints/load-types';
import {
  type Place,
  type PlaceType,
  useCreatePlaceMutation,
  useDeletePlaceMutation,
  useGetPlacesInfiniteQuery,
  useUpdatePlaceMutation,
} from '@/shared/api/endpoints/places';
import { assertHasValue } from '@/shared/lib/assert-has-value';
import { assertNever } from '@/shared/lib/assert-never';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { AppRoutes } from '@/shared/routes/router';
import { Select } from '@/shared/ui/Select';
import { type ColumnDef, ControlPanel, Table, TableProvider } from '@/shared/ui/Table';
import { toast } from '@/shared/ui/Toast';

import { getColumns, type PlaceTableRow } from '../../model/getColumns';

/**
 * Представляет тип для фильтра мест по состояния активности.
 */
type IsActiveFilter = 'true' | 'false' | 'all';

const loadFiler = ['load'] as const;
const parkTransitFiler = ['park', 'transit'] as const;
const unloadReloadFiler = ['unload', 'reload'] as const;

/** Значения фильтров по типу мест. */
const placeTypeFilter = {
  load: loadFiler,
  unload: unloadReloadFiler,
  reload: unloadReloadFiler,
  park: parkTransitFiler,
  transit: parkTransitFiler,
} as const;

/** Значения фильтров по состоянию активности места. */
const isActiveFilter = {
  true: true,
  false: false,
  all: undefined,
} as const;

/**
 * Компонент страницы «Места» (погрузки, разгрузки, стоянки, транзитные).
 * Предоставляет функциональность для просмотра, создания, редактирования и удаления мест
 * с возможностью фильтрации по типу места и состоянию активности.
 * Поддерживает бесконечную прокрутку для загрузки данных постранично.
 */
export function PlacesPage() {
  const [placeType, setPlaceType] = useState<PlaceType>('load');
  const [filterByIsActive, setFilterByIsActive] = useState<IsActiveFilter>('all');

  const {
    data: placesData,
    isLoading,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useGetPlacesInfiniteQuery({
    is_active: isActiveFilter[filterByIsActive],
    types: placeTypeFilter[placeType],
  });

  const [createPlace] = useCreatePlaceMutation();
  const [updatePlace] = useUpdatePlaceMutation();
  const [deletePlace] = useDeletePlaceMutation();

  const { data: cargoData, isLoading: isCargoLoading, isFetching: isCargoFetching } = useGetAllLoadTypeQuery();

  const { data: horizonsData, isLoading: isLoadingHorizons, isFetching: isFetchingHorizons } = useGetAllHorizonsQuery();

  const resolveCargoName = (cargoType: number) => {
    return cargoData?.entities[cargoType]?.name ?? '';
  };

  const resolveHorizonName = (horizonId: number) => {
    return horizonsData?.items.find((horizon) => horizon.id === horizonId)?.name ?? '';
  };

  const places =
    placesData?.pages.flatMap((page) =>
      page.items.map((place) => ({
        ...place,
        cargo_name: hasValue(place.cargo_type) ? resolveCargoName(place.cargo_type) : '',
        horizon_name: hasValue(place.horizon_id) ? resolveHorizonName(place.horizon_id) : '',
      })),
    ) ?? EMPTY_ARRAY;

  const total = placesData?.pages[0]?.total ?? 0;

  // eslint-disable-next-line sonarjs/function-return-type
  const horizonsOptions = useMemo(() => {
    if (horizonsData) {
      return Array.from(horizonsData.items)
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((item) => ({
          value: String(item.id),
          label: item.name,
        }));
    }
    return EMPTY_ARRAY;
  }, [horizonsData]);

  const cargoOptions = cargoData
    ? cargoData.ids
        .map((id) => {
          const item = cargoData.entities[id];
          return { value: String(item.id), label: item.name };
        })
        .sort((a, b) => a.label.localeCompare(b.label))
    : EMPTY_ARRAY;

  const columns: ColumnDef<PlaceTableRow>[] = [...getColumns(placeType, horizonsOptions, cargoOptions)];

  const isTableDataLoading =
    isLoading || isFetching || isLoadingHorizons || isFetchingHorizons || isCargoLoading || isCargoFetching;

  /**
   * Обработчик добавления нового места.
   *
   * @param newPlace Частичные данные нового места для создания.
   */
  const handleAdd = async (newPlace: Partial<Place>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { name, cargo_type } = newPlace;
    const type = placeType === 'load' ? placeType : newPlace.type;
    assertHasValue(name);
    assertHasValue(type);

    const request = createPlace({
      ...newPlace,
      name,
      type,
      cargo_type: hasValue(cargo_type) ? cargo_type : null,
    }).unwrap();

    await toast.promise(request, {
      loading: {
        message: `Добавление нового места «${name}»`,
      },
      success: {
        message: `Добавлено новое место «${name}»`,
      },
      error: {
        message: 'Ошибка добавления',
      },
    });
  };

  /**
   * Обработчик редактирования существующего места.
   *
   * @param id Идентификатор места для обновления.
   * @param updatedData Частичные данные для обновления места.
   */
  const handleEdit = async (id: number | string, updatedData: Partial<Place>) => {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const { name, type, cargo_type } = updatedData;
    assertHasValue(name);
    assertHasValue(type);

    const request = updatePlace({
      placeId: Number(id),
      body: {
        ...updatedData,
        name,
        type,
        cargo_type: hasValue(cargo_type) ? cargo_type : null,
      },
    }).unwrap();

    await toast.promise(request, {
      loading: { message: 'Сохранение изменений' },
      success: { message: 'Изменения сохранены' },
      error: { message: 'Ошибка сохранения' },
    });
  };

  /**
   * Обработчик удаления мест.
   *
   * @param ids Массив идентификаторов мест для удаления.
   */
  const handleDelete = async (ids: (number | string)[]) => {
    await Promise.all(ids.map((id) => deletePlace(Number(id)).unwrap()));
  };

  /**
   * Обработчик изменения фильтра по типу места.
   * При изменении типа сбрасывает фильтр по активности на «Все».
   *
   * @param value Новое значение типа места или null.
   */
  const handleChangePlaceTypeFilter = (value: PlaceType | null) => {
    if (hasValue(value)) {
      setPlaceType(value);
      setFilterByIsActive('all');
    }
  };

  /**
   * Обработчик изменения фильтра активности места.
   *
   * @param value Новое значение фильтра активности или null.
   */
  const handleChangeIsActiveFilter = (value: IsActiveFilter | null) => {
    if (hasValue(value)) {
      setFilterByIsActive(value);
    }
  };

  /**
   * Обработчик прокрутки до конца списка.
   * Загружает следующую страницу данных, если не выполняется загрузка и доступны данные.
   */
  const handleScrollToBottom = () => {
    if (!isFetching && !isFetchingNextPage && hasNextPage) {
      void fetchNextPage();
    }
  };

  return (
    <Page variant="table">
      <TableProvider
        key={placeType}
        data={places}
        columns={columns}
        total={total}
        storageKey={`asu-gtk-${placeType}-places`}
        onAdd={handleAdd}
        onEdit={handleEdit}
        onDelete={handleDelete}
        getRowId={(row) => row.id}
      >
        <Header
          headerClassName="table-header"
          routeKey={AppRoutes.PLACES}
          customName={getPageName(placeType)}
        >
          <ControlPanel
            centerContent={
              <Select
                data={[
                  { label: 'Все', value: 'all' },
                  { label: 'Не выведено', value: 'true' },
                  { label: 'Выведено', value: 'false' },
                ]}
                value={filterByIsActive}
                onChange={handleChangeIsActiveFilter}
                searchable={false}
              />
            }
            afterStatisticsContent={
              <Select
                data={[
                  { label: 'Места погрузки', value: 'load' },
                  { label: 'Места разгрузки/перегрузки', value: 'unload' },
                  { label: 'Места стоянки/транзитные', value: 'park' },
                ]}
                value={placeType}
                onChange={handleChangePlaceTypeFilter}
                searchable={false}
              />
            }
          />
        </Header>
        <div className="table-wrapper">
          <Table
            data={places}
            columns={columns}
            isLoading={isTableDataLoading}
            onScrollToBottom={handleScrollToBottom}
          />
        </div>
      </TableProvider>
    </Page>
  );
}

/**
 * Возвращает название страницы в зависимости от типа места.
 *
 * @param placeType Тип места для определения названия страницы.
 * @returns Название страницы, соответствующее типу места.
 */
function getPageName(placeType: PlaceType) {
  switch (placeType) {
    case 'load':
      return 'Места погрузки';
    case 'unload':
    case 'reload':
      return 'Места разгрузки/перегрузки';
    case 'transit':
    case 'park':
      return 'Места стоянок и транзитные места';
    default:
      assertNever(placeType);
  }
}

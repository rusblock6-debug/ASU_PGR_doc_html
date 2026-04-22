import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import type { Place, PlaceType } from '@/shared/api/endpoints/places';
import { useGetAllPlacesQuery } from '@/shared/api/endpoints/places';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { formatNumber } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import type { SortState } from '@/shared/lib/sort-by-field';
import { sortByField } from '@/shared/lib/sort-by-field';

import { selectHorizonFilter, selectPlaceGroupSorts, selectSelectedHorizonId } from '../../model/selectors';
import { HorizonFilter } from '../../model/types';
import type { ObjectListSortField } from '../../model/types';

/** Тип места с добавленным именем горизонта. */
export type MapPlaceItem = Place & {
  /** Наименование горизонта. */
  readonly horizon_name: string;
  /** Отформатированный остаток, м³ (пустая строка, если отсутствует). */
  readonly stock: string;
};

/** Маппинг UI-полей сортировки на поля модели места. */
const UI_TO_API_FIELD: Partial<Record<ObjectListSortField, string>> = {
  stock: 'current_stock',
  horizon: 'horizon_name',
} as const;

/**
 * Данные мест для страницы карты: загрузка, группировка по типу,
 * сортировка каждой группы по параметрам из Redux.
 */
export function useMapPlaces() {
  const { data, isLoading } = useGetAllPlacesQuery();
  const { data: horizonsData } = useGetAllHorizonsQuery();
  const sorts = useAppSelector(selectPlaceGroupSorts);
  const horizonFilter = useAppSelector(selectHorizonFilter);
  const selectedHorizonId = useAppSelector(selectSelectedHorizonId);

  const horizonsMap = new Map(horizonsData?.items.map((horizon) => [horizon.id, horizon.height]) ?? EMPTY_ARRAY);

  const all = (data?.items ?? EMPTY_ARRAY).filter((place) => place.is_active);
  const filteredAll =
    horizonFilter === HorizonFilter.CURRENT_HORIZON
      ? all.filter((place) => place.horizon_id === selectedHorizonId)
      : all;

  const places = filteredAll.reduce<Record<PlaceType, MapPlaceItem[]>>(
    (acc, place) => {
      const hasStock = 'current_stock' in place && hasValue(place.current_stock);
      const hasHorizon = hasValue(place.horizon_id);

      acc[place.type].push({
        ...place,
        stock: hasStock ? `${formatNumber(place.current_stock)} м³` : '',
        horizon_name: hasHorizon ? `${horizonsMap.get(place.horizon_id)} м` : '',
      });

      return acc;
    },
    { reload: [], load: [], unload: [], park: [], transit: [] },
  );

  const groups = {
    reload: sortByField(places.reload, toApiSort(sorts.reload)),
    load: sortByField(places.load, toApiSort(sorts.load)),
    unload: sortByField(places.unload, toApiSort(sorts.unload)),
    park: sortByField(places.park, toApiSort(sorts.park)),
    transit: sortByField(places.transit, toApiSort(sorts.transit)),
  };

  const sortedHorizons = sortByField(horizonsData?.items ?? EMPTY_ARRAY, { field: 'height', order: 'desc' });
  const sortedAll = sortByField(all, { field: 'name', order: 'asc' });

  return { groups, all: sortedAll, isLoading, sorts, horizons: sortedHorizons };
}

/**
 * Трансформирует из UI-имён колонок в имена полей API.
 */
function toApiSort(sort: SortState<ObjectListSortField>) {
  return { field: UI_TO_API_FIELD[sort.field] ?? sort.field, order: sort.order };
}

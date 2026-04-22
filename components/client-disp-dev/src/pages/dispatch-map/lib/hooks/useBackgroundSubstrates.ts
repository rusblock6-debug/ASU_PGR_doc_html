import { useGetAllHorizonsQuery } from '@/shared/api/endpoints/horizons';
import type { SubstrateResponse } from '@/shared/api/endpoints/substrates';
import { useGetSubstratesInfiniteQuery } from '@/shared/api/endpoints/substrates';
import { EMPTY_ARRAY, NO_DATA } from '@/shared/lib/constants';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { sortByField } from '@/shared/lib/sort-by-field';
import type { SelectOption } from '@/shared/ui/types';

import { selectBackgroundSort } from '../../model/selectors';
import { mapActions } from '../../model/slice';
import type { BackgroundSortField } from '../../model/types';

/**
 * Элемент списка подложек с предвычисленными полями для сортировки.
 */
type BackgroundListItem = SubstrateResponse & {
  /** Название для отображения. */
  readonly name: string;
  /** Значение горизонта. */
  readonly horizon: number | null;
};

/**
 * Хук для загрузки списка подложек и горизонтов с учётом сортировки из Redux.
 * Возвращает уже отсортированный список и опции для селектов горизонтов.
 */
export function useBackgroundSubstrates() {
  const dispatch = useAppDispatch();
  const sortState = useAppSelector(selectBackgroundSort);

  const { data: substratesData } = useGetSubstratesInfiniteQuery();
  const { data: horizonsData } = useGetAllHorizonsQuery();

  const substrates = substratesData?.pages.flatMap((page) => page.items) ?? [];
  const horizons = horizonsData?.items ? [...horizonsData.items].sort((a, b) => a.height - b.height) : EMPTY_ARRAY;

  const backgroundItems = substrates.map((item) => ({
    ...item,
    name: item.original_filename,
    horizon: hasValue(item.horizon_id) ? item.horizon_id : Number.MIN_SAFE_INTEGER,
  }));

  const sortedSubstrates: readonly SubstrateResponse[] = sortByField<BackgroundListItem>(backgroundItems, sortState);

  const horizonOptions = horizons.map((item) => ({
    value: String(item.id),
    label: `${item.height} м`,
  }));

  const selectOptions: SelectOption[] = [{ label: NO_DATA.LONG_DASH, value: '' }, ...horizonOptions];

  const handleSortChange = (field: BackgroundSortField) => {
    dispatch(mapActions.toggleGroupSort({ entity: 'background', field }));
  };

  return {
    substrates,
    sortedSubstrates,
    selectOptions,
    sortState,
    horizons,
    handleSortChange,
  };
}

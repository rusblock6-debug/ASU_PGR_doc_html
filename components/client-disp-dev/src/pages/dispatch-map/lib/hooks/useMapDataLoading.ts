import { skipToken } from '@reduxjs/toolkit/query';

import { useGetAllHorizonsQuery, useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectSelectedHorizonId } from '../../model/selectors';

/**
 * Агрегирует состояние загрузки критичных данных для {@link MapScene}.
 *
 * Показывает загрузку, пока нет данных для текущего горизонта (первое открытие).
 * При возврате на закэшированный горизонт данные отображаются мгновенно.
 * Фоновый рефетч того же горизонта (например, после сохранения) лоадер не показывает.
 */
export function useMapDataLoading() {
  const horizonId = useAppSelector(selectSelectedHorizonId);

  const { isLoading: isHorizonsLoading } = useGetAllHorizonsQuery();
  const { isFetching: isGraphFetching, currentData: graphData } = useGetHorizonGraphQuery(horizonId ?? skipToken);

  return isHorizonsLoading || (isGraphFetching && !graphData);
}

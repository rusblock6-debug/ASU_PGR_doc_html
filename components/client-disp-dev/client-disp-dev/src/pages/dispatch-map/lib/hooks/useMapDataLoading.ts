import { skipToken } from '@reduxjs/toolkit/query';

import { useGetAllHorizonsQuery, useGetHorizonGraphQuery } from '@/shared/api/endpoints/horizons';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectSelectedHorizonId } from '../../model/selectors';

/**
 * Агрегирует состояние загрузки критичных данных для {@link MapScene}.
 *
 * Ожидает загрузку горизонтов и графа уровня — без них ни один слой карты не отрисуется.
 */
export function useMapDataLoading() {
  const { isLoading: isHorizonsLoading } = useGetAllHorizonsQuery();
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const { isLoading: isGraphLoading } = useGetHorizonGraphQuery(horizonId ?? skipToken);

  return isHorizonsLoading || isGraphLoading;
}

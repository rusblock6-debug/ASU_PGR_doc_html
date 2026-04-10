import { skipToken } from '@reduxjs/toolkit/query';
import { useMemo } from 'react';
import { useSelector } from 'react-redux';

import { useGetSubstratesInfiniteQuery, useGetSubstrateByIdQuery } from '@/shared/api/endpoints/substrates';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';

import { selectBackgroundPreviewOpacity, selectSelectedHorizonId } from '../../model/selectors';
import { DEFAULT_CENTER, toScene } from '../coordinates';

const OPACITY_MAX = 100;

/**
 * Собирает данные для отрисовки подложки текущего горизонта.
 * Возвращает пропсы для BackgroundLayer или null, если подложку рендерить не нужно.
 */
export function useBackgroundLayer() {
  const horizonId = useAppSelector(selectSelectedHorizonId);
  const previewOpacity = useSelector(selectBackgroundPreviewOpacity);

  const { data: substratesPages } = useGetSubstratesInfiniteQuery();
  const substrates = useMemo(
    () => substratesPages?.pages.flatMap((page) => page.items) ?? EMPTY_ARRAY,
    [substratesPages],
  );

  const currentSubstrate = horizonId ? (substrates.find((item) => item.horizon_id === horizonId) ?? null) : null;

  const { data: substrateDetails } = useGetSubstrateByIdQuery(currentSubstrate?.id ?? skipToken);

  const savedOpacity = currentSubstrate?.opacity ?? OPACITY_MAX;
  const normalizedOpacity = Math.min(1, Math.max(0, (previewOpacity ?? savedOpacity) / OPACITY_MAX));

  if (!horizonId || !currentSubstrate || !substrateDetails?.svg_link) {
    return null;
  }

  const apiCenter = substrateDetails.center;
  const hasCenterFromApi = apiCenter.x !== 0 || apiCenter.y !== 0;

  let centerX: number, centerZ: number;

  if (hasCenterFromApi) {
    const [cx, , cz] = toScene(apiCenter.x, apiCenter.y);
    centerX = cx;
    centerZ = cz;
  } else {
    const [cx, , cz] = toScene(DEFAULT_CENTER.LONGITUDE, DEFAULT_CENTER.LATITUDE);
    centerX = cx;
    centerZ = cz;
  }

  return {
    url: substrateDetails.svg_link,
    opacity: normalizedOpacity,
    centerX,
    centerZ,
  };
}

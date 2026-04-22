import { useEffect, useMemo, useRef, useState } from 'react';

import {
  type MapPlayerPlaybackItem,
  useLazyGetMapPlayerPlaybackChunkByIndexQuery,
  useLazyGetMapPlayerPlaybackManifestQuery,
  useLazyGetMapPlayerPlaybackQuery,
} from '@/shared/api/endpoints/map-player';
import { assertNever } from '@/shared/lib/assert-never';
import { EMPTY_ARRAY } from '@/shared/lib/constants';
import { getMapGroupedByField } from '@/shared/lib/get-map-grouped-by-field';
import { hasValue } from '@/shared/lib/has-value';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';
import { useAppSelector } from '@/shared/lib/hooks/useAppSelector';
import { normalizeISODateTimeWithoutMilliseconds } from '@/shared/lib/timezone';
import { toast } from '@/shared/ui/Toast';

import {
  selectSelectedVehicleHistoryIds,
  selectHistoryRangeFilter,
  selectIsVisibleHistoryPlayer,
  selectPlayerCurrentTime,
  selectVehicleHistoryMarks,
} from '../../model/selectors';
import { mapActions } from '../../model/slice';

/** Представляет метаданные манифеста истории. */
interface ManifestMeta {
  /** Возвращает хэш. */
  readonly hash: string;
  /** Возвращает продолжительность одного чанка, в секундах. */
  readonly chunkDurationSec: number;
  /** Возвращает ожидаемое общее количество чанков. */
  readonly totalChunksCount: number;
}

const TWO_MINUTES_MS = 1000 * 60 * 2;
const TEN_SECONDS_MS = 1000 * 10;

/**
 * Собирает данные о положении и статусе машин.
 */
export function useMapVehicleHistoryState() {
  const dispatch = useAppDispatch();

  const dateRangeFilter = useAppSelector(selectHistoryRangeFilter);
  const checkedVehicleHistoryIds = useAppSelector(selectSelectedVehicleHistoryIds);
  const isVisibleHistoryPlayer = useAppSelector(selectIsVisibleHistoryPlayer);
  const playerCurrentTime = useAppSelector(selectPlayerCurrentTime);
  const vehicleHistoryMarks = useAppSelector(selectVehicleHistoryMarks);

  const [getMapPlayerPlayback, { isLoading: isLoadingMapPlayerPlayback }] = useLazyGetMapPlayerPlaybackQuery();
  const [getMapPlayerPlaybackManifest, { isLoading: isLoadingMapPlayerPlaybackManifest }] =
    useLazyGetMapPlayerPlaybackManifestQuery();
  const [getMapPlayerPlaybackChunkByIndex, { isLoading: isLoadingMapPlayerPlaybackChunkByIndex }] =
    useLazyGetMapPlayerPlaybackChunkByIndexQuery();

  const [manifestMeta, setManifestMeta] = useState<ManifestMeta | null>(null);

  const [data, setData] = useState<Map<string, readonly MapPlayerPlaybackItem[]> | null>(null);

  const hasLoadedInitialChunksRef = useRef(false);

  useEffect(() => {
    if (!dateRangeFilter || !isVisibleHistoryPlayer) return;

    let isCancelled = false;

    // eslint-disable-next-line sonarjs/cognitive-complexity
    const fetchManifestMeta = async () => {
      try {
        dispatch(mapActions.toggleLoading(true));

        const mapPlayerPlayback = await getMapPlayerPlayback({
          start_date: dateRangeFilter.from,
          end_date: dateRangeFilter.to,
          vehicle_ids: checkedVehicleHistoryIds,
        }).unwrap();

        if (isCancelled) return;

        switch (mapPlayerPlayback.status) {
          case 'ready': {
            setManifestMeta({
              hash: mapPlayerPlayback.hash,
              chunkDurationSec: mapPlayerPlayback.chunk_duration_sec,
              totalChunksCount: mapPlayerPlayback.total_chunk_counts,
            });
            return;
          }

          case 'processing': {
            dispatch(mapActions.setLoadPercentage(0));

            while (!isCancelled) {
              const manifest = await getMapPlayerPlaybackManifest({
                hash: mapPlayerPlayback.hash,
              }).unwrap();

              const totalChunksCount = manifest.total_chunk_counts;
              const chunksCount = manifest.chunk_count;

              const percentage =
                totalChunksCount > 0 && chunksCount > 0 ? Math.round((chunksCount / totalChunksCount) * 100) : 0;

              dispatch(mapActions.setLoadPercentage(percentage));

              if (isCancelled) return;

              if (manifest.status === 'ready') {
                setManifestMeta({
                  hash: manifest.hash,
                  chunkDurationSec: manifest.chunk_duration_sec,
                  totalChunksCount: manifest.total_chunk_counts,
                });
                dispatch(mapActions.setLoadPercentage(100));
                return;
              }

              if (manifest.status === 'error') {
                toast.error({ message: 'Возникла ошибка при получении истории.' });
                dispatch(mapActions.toggleLoading(false));
                dispatch(mapActions.setLoadPercentage(null));
                return;
              }

              await new Promise((resolve) => setTimeout(resolve, 1000));
            }
            return;
          }

          case 'error': {
            toast.error({ message: 'Возникла ошибка при получении истории.' });
            return;
          }

          default:
            assertNever(mapPlayerPlayback.status);
        }
      } catch {
        toast.error({ message: 'Возникла ошибка при получении истории.' });
        dispatch(mapActions.toggleLoading(false));
        dispatch(mapActions.setLoadPercentage(null));
      }
    };

    void fetchManifestMeta();

    return () => {
      isCancelled = true;
    };
  }, [
    checkedVehicleHistoryIds,
    dateRangeFilter,
    dispatch,
    getMapPlayerPlayback,
    getMapPlayerPlaybackManifest,
    isVisibleHistoryPlayer,
  ]);

  const currentChunkIndex = useMemo(() => {
    if (!dateRangeFilter || !hasValue(playerCurrentTime) || !manifestMeta) return null;

    return Math.floor(
      (playerCurrentTime - new Date(dateRangeFilter.from).getTime()) / (manifestMeta.chunkDurationSec * 1000),
    );
  }, [dateRangeFilter, manifestMeta, playerCurrentTime]);

  useEffect(() => {
    if (!manifestMeta || !hasValue(currentChunkIndex)) return;

    const fetchData = async () => {
      const requests = [
        currentChunkIndex - 1 >= 0
          ? getMapPlayerPlaybackChunkByIndex({
              hash: manifestMeta.hash,
              chunkIndex: currentChunkIndex - 1,
            }).unwrap()
          : null,

        currentChunkIndex < manifestMeta.totalChunksCount
          ? getMapPlayerPlaybackChunkByIndex({
              hash: manifestMeta.hash,
              chunkIndex: currentChunkIndex,
            }).unwrap()
          : null,

        currentChunkIndex + 1 < manifestMeta.totalChunksCount
          ? getMapPlayerPlaybackChunkByIndex({
              hash: manifestMeta.hash,
              chunkIndex: currentChunkIndex + 1,
            }).unwrap()
          : null,
      ].filter(hasValue);

      const results = await Promise.allSettled(requests);

      const fulfilled = results.filter((r) => r.status === 'fulfilled').flatMap((r) => r.value.data);

      const rejected = results.filter((r) => r.status === 'rejected');

      if (rejected.length === results.length) {
        toast.error({ message: 'Отсутствуют данные по выбранному диапазону.' });
      }

      if (!hasLoadedInitialChunksRef.current) {
        hasLoadedInitialChunksRef.current = true;
      }

      dispatch(mapActions.toggleLoading(false));
      dispatch(mapActions.setLoadPercentage(null));

      setData(getMapGroupedByField(fulfilled, 'timestamp'));
    };

    void fetchData();
  }, [currentChunkIndex, dispatch, getMapPlayerPlaybackChunkByIndex, manifestMeta]);

  useEffect(() => {
    if (!isVisibleHistoryPlayer) {
      setData(null);
      setManifestMeta(null);
      hasLoadedInitialChunksRef.current = false;
    }
  }, [dispatch, isVisibleHistoryPlayer]);

  const vehicleHistoryItems = playerCurrentTime
    ? (data?.get(normalizeISODateTimeWithoutMilliseconds(new Date(playerCurrentTime))) ?? EMPTY_ARRAY)
    : EMPTY_ARRAY;

  useEffect(() => {
    if (hasValue(playerCurrentTime)) {
      const filtered = vehicleHistoryMarks.filter((item) => {
        const timeDifference = playerCurrentTime - new Date(item.timestamp).getTime();
        return timeDifference >= 0 && timeDifference < TWO_MINUTES_MS;
      });

      const lastVehicleHistoryMark = vehicleHistoryMarks.at(-1);

      if (
        vehicleHistoryItems.length > 0 &&
        (!lastVehicleHistoryMark ||
          playerCurrentTime - new Date(lastVehicleHistoryMark.timestamp).getTime() >= TEN_SECONDS_MS)
      ) {
        dispatch(mapActions.setVehicleHistoryMarks([...filtered, ...vehicleHistoryItems]));
        return;
      }

      dispatch(mapActions.setVehicleHistoryMarks(filtered));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vehicleHistoryItems, dispatch, playerCurrentTime]);

  return {
    data: vehicleHistoryItems,
    isLoading:
      isLoadingMapPlayerPlayback || isLoadingMapPlayerPlaybackManifest || isLoadingMapPlayerPlaybackChunkByIndex,
  };
}

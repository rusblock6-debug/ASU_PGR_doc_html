import { useGetRoutesStreamQuery } from '@/shared/api/endpoints/routes';

/** Подписка на Graph SSE `/graph-api/api/events/stream/routes` (дистанция и ETA). */
export const useRoutesStreamSse = () => {
  useGetRoutesStreamQuery();
};

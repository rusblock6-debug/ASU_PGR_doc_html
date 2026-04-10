import { useEffect } from 'react';

import { subscribeRoutesStreamSse } from '@/shared/api/sse/routes-stream-sse';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

/** Подписка на Graph SSE `/graph-api/api/events/stream/routes` (дистанция и ETA). Только там, где нужен UI. */
export const useRoutesStreamSse = () => {
  const dispatch = useAppDispatch();

  useEffect(() => {
    return subscribeRoutesStreamSse(dispatch);
  }, [dispatch]);
};

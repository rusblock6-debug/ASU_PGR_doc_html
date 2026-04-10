import { useEffect, useRef } from 'react';

import { subscribeShiftTasksSse } from '@/shared/api/sse/shift-tasks-sse';
import type { ShiftTaskChangedSsePayload } from '@/shared/api/types/trip-service';
import { useAppDispatch } from '@/shared/lib/hooks/useAppDispatch';

/**
 * Подписка на SSE наряд-заданий в dev/prod (тот же origin, что и API).
 * Колбэк не переподключает стрим: хранится в ref.
 */
export const useShiftTasksSse = (onPayload?: (payload: ShiftTaskChangedSsePayload) => void) => {
  const dispatch = useAppDispatch();
  const onPayloadRef = useRef(onPayload);
  onPayloadRef.current = onPayload;

  useEffect(() => {
    return subscribeShiftTasksSse(dispatch, {
      onPayload: (p) => onPayloadRef.current?.(p),
    });
  }, [dispatch]);
};

import { useCallback, useEffect, useRef, useState } from 'react';

const HIGHLIGHT_DURATION_MS = 2000;

/**
 * Хук для управления подсветкой карточек транспорта.
 * Подсветка автоматически снимается через заданное время.
 */
export function useHighlightedVehicles() {
  const [highlightedIds, setHighlightedIds] = useState<Set<number>>(new Set());
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const removeHighlight = useCallback((vehicleId: number) => {
    setHighlightedIds((prev) => {
      const next = new Set(prev);
      next.delete(vehicleId);
      return next;
    });
    timersRef.current.delete(vehicleId);
  }, []);

  const addHighlight = useCallback(
    (vehicleId: number) => {
      const existingTimer = timersRef.current.get(vehicleId);
      if (existingTimer) {
        clearTimeout(existingTimer);
      }

      setHighlightedIds((prev) => new Set(prev).add(vehicleId));

      const timer = setTimeout(() => {
        removeHighlight(vehicleId);
      }, HIGHLIGHT_DURATION_MS);

      timersRef.current.set(vehicleId, timer);
    },
    [removeHighlight],
  );

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      for (const timer of timers.values()) {
        clearTimeout(timer);
      }
      timers.clear();
    };
  }, []);

  return { highlightedIds, addHighlight };
}

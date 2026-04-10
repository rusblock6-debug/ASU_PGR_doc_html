import { useRef, useCallback, useEffect } from 'react';

type Timeout = ReturnType<typeof setTimeout>;

/**
 * Представляет хук для отложенного срабатывания функции.
 *
 * @param delay задержка срабатывания в миллисекундах.
 */
export function useDebouncedCallback(delay = 300) {
  const timeoutRef = useRef<Timeout | null>(null);

  const debounced = useCallback(
    (fn: () => void) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        fn();
      }, delay);
    },
    [delay],
  );

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return debounced;
}

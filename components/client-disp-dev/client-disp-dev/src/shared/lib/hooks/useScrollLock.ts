import React, { useEffect } from 'react';

/**
 * Хук для блокировки скролла в контейнере
 */
export function useScrollLock(locked: boolean, ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    if (!locked || !ref.current) return;

    const element = ref.current;
    const originalOverflow = element.style.overflow;
    element.style.overflow = 'hidden';

    return () => {
      element.style.overflow = originalOverflow;
    };
    // ref — стабильный объект, не нужен в зависимостях
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locked]);
}

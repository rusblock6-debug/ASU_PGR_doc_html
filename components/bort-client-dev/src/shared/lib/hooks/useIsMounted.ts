import { useEffect, useState } from 'react';

/**
 * Хук, который проверяет смонтирован ли компонент.
 */
export function useIsMounted() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    return () => {
      setIsMounted(false);
    };
  }, []);

  return isMounted;
}

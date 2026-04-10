import { useEffect, useState } from 'react';

/**
 * Хук для определения состояния подключения к сети.
 * Использует Navigator Online API и слушает события online/offline.
 *
 * @returns true если есть подключение к сети, false если нет
 */
export function useNetworkStatus(): boolean {
  const [isOnline, setIsOnline] = useState(() => {
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  });

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}

import { useEffect, useState } from 'react';

import { useTimezone } from '@/shared/lib/hooks/useTimezone';

/**
 * Хук для получения текущей даты и времени в Московской временной зоне.
 * Обновляется каждую секунду.
 *
 * @returns Строка формата "28.11.2025 • 14:58:09 (UTC+3)"
 */
export function useCurrentTime(): string {
  const tz = useTimezone();
  const [currentTime, setCurrentTime] = useState(() => formatCurrentTime(tz));

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(formatCurrentTime(tz));
    }, 1000);

    return () => clearInterval(interval);
  }, [tz]);

  return currentTime;
}

function formatCurrentTime(tz: ReturnType<typeof useTimezone>): string {
  const now = new Date();
  const date = tz.formatDate(now); // dd.MM.yyyy
  const time = tz.formatTime(now); // HH:mm:ss

  return `${date} • ${time} (UTC+3)`;
}

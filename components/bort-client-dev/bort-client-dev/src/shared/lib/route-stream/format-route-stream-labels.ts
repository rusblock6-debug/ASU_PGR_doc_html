import { NO_DATA } from '@/shared/lib/constants';

/**
 * Части подписи «~N км» для главного экрана (макет kiosk). null — нет данных со стрима.
 */
export const getRouteStreamDistanceKmParts = (meters: number | null) => {
  if (meters == null || !Number.isFinite(meters)) {
    return null;
  }

  const km = Math.max(0, meters / 1000);
  const value =
    km >= 10
      ? String(Math.round(km))
      : new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1, minimumFractionDigits: 0 }).format(
          Math.round(km * 10) / 10,
        );

  return { value, unit: 'км' };
};

/**
 * Части подписи «~N мин» из секунд стрима.
 */
export const getRouteStreamDurationMinutesParts = (seconds: number | null) => {
  if (seconds == null || !Number.isFinite(seconds)) {
    return null;
  }

  const minutes = Math.max(0, Math.round(seconds / 60));
  return { value: String(minutes), unit: 'мин' };
};

/**
 * Части подписи «~N мин» из секунд: минуты округляются вверх (детали маршрута / ETA).
 */
export const getRouteStreamDurationMinutesCeilParts = (seconds: number | null) => {
  if (seconds == null || !Number.isFinite(seconds)) {
    return null;
  }

  const minutes = Math.max(0, Math.ceil(seconds / 60));
  return { value: String(minutes), unit: 'мин' };
};

/**
 * Подпись расстояния до точки (метры), для главного экрана.
 */
export const formatRouteStreamDistanceMeters = (meters: number | null) => {
  if (meters == null || !Number.isFinite(meters)) {
    return NO_DATA.LONG_DASH;
  }

  const rounded = Math.round(meters);
  return `${new Intl.NumberFormat('ru-RU').format(rounded)} м`;
};

/**
 * Подпись оставшегося времени (секунды из стрима).
 */
export const formatRouteStreamDurationSeconds = (seconds: number | null) => {
  if (seconds == null || !Number.isFinite(seconds)) {
    return NO_DATA.LONG_DASH;
  }

  const total = Math.max(0, Math.round(seconds));
  if (total < 60) {
    return `${total} сек`;
  }

  const minutes = Math.floor(total / 60);
  if (minutes < 60) {
    return `${minutes} мин`;
  }

  const hours = Math.floor(minutes / 60);
  const restMin = minutes % 60;
  return restMin > 0 ? `${hours} ч ${restMin} мин` : `${hours} ч`;
};

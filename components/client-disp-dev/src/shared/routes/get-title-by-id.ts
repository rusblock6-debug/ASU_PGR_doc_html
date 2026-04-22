import { getPageTitle } from '@/shared/routes/navigation';
import { type AppRouteType, getRouteByKey } from '@/shared/routes/router';

/**
 * Получает заголовок страницы по id
 * Шаги: id → url → title (через getPageTitle)
 *
 * @example fleet_control → Fleet Control
 */
export function getTitleById(id: AppRouteType): string {
  try {
    const url = getRouteByKey(id);
    const title = getPageTitle(url.PATH());
    return title || formatIdAsTitle(id);
  } catch {
    return formatIdAsTitle(id);
  }
}

/**
 * Преобразует id в читаемый заголовок для fallback
 *
 * @example fleet_control → Fleet Control
 */
function formatIdAsTitle(id: string): string {
  return id
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

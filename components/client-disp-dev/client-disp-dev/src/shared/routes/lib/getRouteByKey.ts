import type { AppRouteType } from '../router';
import { ROUTES } from '../router';

type RouteConfig = (typeof ROUTES)[keyof typeof ROUTES];

/**
 * Маппинг ключей маршрутов на их конфигурации для быстрого поиска.
 * Инициализируется лениво при первом вызове getRouteByKey.
 */
// eslint-disable-next-line @typescript-eslint/naming-convention
let ROUTES_BY_KEY: Record<AppRouteType, RouteConfig> | null = null;

/**
 * Получает конфигурацию маршрута по его ключу
 *
 * @param key - Ключ маршрута (например, 'main', 'settings', 'workspace')
 * @returns Объект конфигурации маршрута с полями KEY и PATH
 * @example
 * const mainRoute = getRouteByKey('main');
 * mainRoute.PATH(); // '/'
 */
export function getRouteByKey(key: AppRouteType) {
  const routesMap = initRoutesMap();
  return routesMap[key];
}

/**
 * Инициализирует маппинг ключей маршрутов
 */
function initRoutesMap() {
  if (!ROUTES_BY_KEY) {
    ROUTES_BY_KEY = Object.fromEntries(Object.values(ROUTES).map((route) => [route.KEY, route])) as Record<
      AppRouteType,
      RouteConfig
    >;
  }
  return ROUTES_BY_KEY;
}

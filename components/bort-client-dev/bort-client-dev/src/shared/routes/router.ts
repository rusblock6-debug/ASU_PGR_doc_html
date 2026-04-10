import { createRoute } from './lib/createRoute';

/**
 * Функции для генерации путей маршрутов приложения
 */
export const getRouteLogin = () => `/login`;

export const getRouteMain = () => `/main`;

export const getRouteMainMenu = () => `/main-menu`;

export const getRouteWorkOrders = () => `/work-orders`;

export const getRouteWorkOrderDetail = (taskId: string) => `/work-orders/${taskId}`;

export const getRouteSessionEnded = () => `/session-ended`;

export const getRouteStats = () => `/stats`;

export const getRouteVehicleStatus = () => `/vehicle-status`;

export const getRouteDowntimeSelect = () => `/downtime-select`;

export const getRouteActiveDowntime = () => `/active-downtime`;

/**
 * Конфигурация всех маршрутов приложения
 */
export const ROUTES = {
  LOGIN: createRoute('login', getRouteLogin),
  MAIN: createRoute('main', getRouteMain),
  MAIN_MENU: createRoute('main_menu', getRouteMainMenu),
  STATS: createRoute('stats', getRouteStats),
  VEHICLE_STATUS: createRoute('vehicle_status', getRouteVehicleStatus),
  DOWNTIME_SELECT: createRoute('downtime_select', getRouteDowntimeSelect),
  ACTIVE_DOWNTIME: createRoute('active_downtime', getRouteActiveDowntime),
  WORK_ORDERS: createRoute('work_orders', getRouteWorkOrders),
  WORK_ORDER_DETAIL: createRoute('work_order_detail', getRouteWorkOrderDetail),
  SESSION_ENDED: createRoute('session_ended', getRouteSessionEnded),
  NOT_FOUND: createRoute('not_found', () => '*'),
} as const;

/**
 * Enum-подобный объект с ключами маршрутов для удобного использования
 *
 * @example
 * const key = AppRoutes.WORK_ORDERS; // 'work_orders'
 */
export const AppRoutes = Object.fromEntries(Object.entries(ROUTES).map(([k, v]) => [k, v.KEY])) as {
  [K in keyof typeof ROUTES]: (typeof ROUTES)[K]['KEY'];
};

/**
 * Тип ключа маршрута (union type всех возможных ключей)
 */
export type AppRouteType = (typeof AppRoutes)[keyof typeof AppRoutes];

/**
 * Проверка является ли строка валидным ключом маршрута приложения.
 */
export function isAppRoute(value: string): value is AppRouteType {
  return Object.values(AppRoutes).includes(value as AppRouteType);
}

export { getRouteByKey } from './lib/getRouteByKey';

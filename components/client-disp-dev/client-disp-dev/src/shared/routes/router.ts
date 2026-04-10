import { createRoute } from './lib/createRoute';

/**
 * Имя главного роута приложения "АСУ ПГР".
 */
const APP_ROUTE_NAME = 'app';

/**
 * Функции для генерации путей маршрутов приложения
 */
export const getRouteMain = () => '/';
export const getRouteApp = () => `/${APP_ROUTE_NAME}`;
export const getRouteSettings = (id?: string) => `/${APP_ROUTE_NAME}/settings/${id}`;
export const getRouteForbidden = () => `/${APP_ROUTE_NAME}/forbidden`;
export const getRouteWorkspace = () => `/${APP_ROUTE_NAME}/workspace`;
export const getRouteFleetControl = () => `/${APP_ROUTE_NAME}/fleet-control`;
export const getRouteTimeMap = () => `/${APP_ROUTE_NAME}/time-map`;
export const getRouteTripEditor = () => `/${APP_ROUTE_NAME}/trip-editor`;
export const getRouteEquipment = () => `/${APP_ROUTE_NAME}/equipment`;
export const getRouteLearning = () => `/learning`;
export const getRouteVGOK = () => `/vgok`;
export const getRouteDispatchersReport = () => `/${APP_ROUTE_NAME}/dispatchers-report`;
export const getRouteDispatchMap = () => `/${APP_ROUTE_NAME}/new-map`;
export const getRouteMap = () => `/${APP_ROUTE_NAME}/map`;
export const getRouteWorkTimeMap = () => `/${APP_ROUTE_NAME}/work-time-map`;
export const getRouteWorkOrder = () => `/${APP_ROUTE_NAME}/work-order`;
export const getRoutePlaces = () => `/${APP_ROUTE_NAME}/places`;
export const getRouteTags = () => `/${APP_ROUTE_NAME}/tags`;
export const getRouteCargo = () => `/${APP_ROUTE_NAME}/cargo`;
export const getRouteHorizons = () => `/${APP_ROUTE_NAME}/horizons`;
export const getRouteStatuses = () => `/${APP_ROUTE_NAME}/statuses`;
export const getRouteSections = () => `/${APP_ROUTE_NAME}/sections`;
export const getRouteRoles = () => `/${APP_ROUTE_NAME}/roles`;
export const getRouteStaff = () => `/${APP_ROUTE_NAME}/staff`;

/**
 * Конфигурация всех маршрутов приложения
 */
export const ROUTES = {
  MAIN: createRoute('main', getRouteMain),
  APP: createRoute('app', getRouteApp),
  DISPATCHERS_REPORT: createRoute('dispatchers_report', getRouteDispatchersReport),
  FLEET_CONTROL: createRoute('fleet_control', getRouteFleetControl),
  DISPATCH_MAP: createRoute('dispatch_map', getRouteDispatchMap),
  MAP: createRoute('map', getRouteMap),
  WORK_TIME_MAP: createRoute('work_time_map', getRouteWorkTimeMap),
  TRIP_EDITOR: createRoute('trip_editor', getRouteTripEditor),
  EQUIPMENT: createRoute('equipment', getRouteEquipment),
  WORK_ORDER: createRoute('work_order', getRouteWorkOrder),
  SETTINGS: createRoute('settings', getRouteSettings),
  FORBIDDEN: createRoute('forbidden', getRouteForbidden),
  WORKSPACE: createRoute('workspace', getRouteWorkspace),
  TIME_MAP: createRoute('time_map', getRouteTimeMap),
  LEARNING: createRoute('learning', getRouteLearning),
  VGOK: createRoute('vgok', getRouteVGOK),
  PLACES: createRoute('places', getRoutePlaces),
  TAGS: createRoute('tags', getRouteTags),
  CARGO: createRoute('cargo', getRouteCargo),
  HORIZONS: createRoute('horizons', getRouteHorizons),
  STATUSES: createRoute('statuses', getRouteStatuses),
  SECTIONS: createRoute('sections', getRouteSections),
  ROLES: createRoute('roles', getRouteRoles),
  STAFF: createRoute('staff', getRouteStaff),
  NOT_FOUND: createRoute('not_found', () => '*'),
} as const;

/**
 * Enum-подобный объект с ключами маршрутов для удобного использования
 *
 * @example
 * const key = AppRoutes.MAIN; // 'main'
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

/** ID элементов kiosk-навигации на экране деталей маршрута (согласованы с RouteTaskActionPanel). */
export const ROUTE_DETAIL_KIOSK_ITEM_IDS = ['action-cancel', 'action-pause', 'action-primary'] as const;

export type RouteDetailKioskItemId = (typeof ROUTE_DETAIL_KIOSK_ITEM_IDS)[number];

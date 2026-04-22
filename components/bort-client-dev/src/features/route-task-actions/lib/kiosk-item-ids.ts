export const ACTION = {
  START: 'action-start',
  PAUSE: 'action-pause',
  COMPLETE: 'action-complete',
  CANCEL: 'action-cancel',
} as const;

/** ID элементов kiosk-навигации на экране деталей маршрута (согласованы с RouteTaskActionPanel). */
export const ROUTE_DETAIL_KIOSK_ITEM_IDS = [ACTION.START, ACTION.PAUSE, ACTION.COMPLETE, ACTION.CANCEL] as const;

export type RouteDetailKioskItemId = (typeof ROUTE_DETAIL_KIOSK_ITEM_IDS)[number];

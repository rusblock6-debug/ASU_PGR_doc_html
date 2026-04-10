import type { RouteProps } from 'react-router-dom';

import { ActiveDowntimePage } from '@/pages/active-downtime';
import { DowntimeSelectPage } from '@/pages/downtime-select';
import { LoginPage } from '@/pages/login';
import { MainMenuPage } from '@/pages/main-menu';
import { SessionEndedPage } from '@/pages/session-ended';
import { StatsPage } from '@/pages/stats';
import { VehicleStatusPage } from '@/pages/vehicle-status';

import {
  type AppRouteType,
  AppRoutes,
  getRouteActiveDowntime,
  getRouteDowntimeSelect,
  getRouteLogin,
  getRouteMain,
  getRouteMainMenu,
  getRouteSessionEnded,
  getRouteStats,
  getRouteVehicleStatus,
  getRouteWorkOrderDetail,
  getRouteWorkOrders,
} from '@/shared/routes/router';

import { MainScreenGuard } from '../ui/MainScreenGuard';
import { WorkOrderDetailGuard } from '../ui/WorkOrderDetailGuard';
import { WorkOrdersGuard } from '../ui/WorkOrdersGuard';

/** Расширенные свойства маршрута. */
export type AppRoutesProps = RouteProps;

export const routeConfig: Record<AppRouteType, AppRoutesProps> = {
  [AppRoutes.LOGIN]: {
    path: getRouteLogin(),
    element: <LoginPage />,
  },
  [AppRoutes.MAIN]: {
    path: getRouteMain(),
    element: <MainScreenGuard />,
  },
  [AppRoutes.MAIN_MENU]: {
    path: getRouteMainMenu(),
    element: <MainMenuPage />,
  },
  [AppRoutes.WORK_ORDERS]: {
    path: getRouteWorkOrders(),
    element: <WorkOrdersGuard />,
  },
  [AppRoutes.WORK_ORDER_DETAIL]: {
    path: getRouteWorkOrderDetail(':taskId'),
    element: <WorkOrderDetailGuard />,
  },
  [AppRoutes.SESSION_ENDED]: {
    path: getRouteSessionEnded(),
    element: <SessionEndedPage />,
  },
  [AppRoutes.STATS]: {
    path: getRouteStats(),
    element: <StatsPage />,
  },
  [AppRoutes.VEHICLE_STATUS]: {
    path: getRouteVehicleStatus(),
    element: <VehicleStatusPage />,
  },
  [AppRoutes.DOWNTIME_SELECT]: {
    path: getRouteDowntimeSelect(),
    element: <DowntimeSelectPage />,
  },
  [AppRoutes.ACTIVE_DOWNTIME]: {
    path: getRouteActiveDowntime(),
    element: <ActiveDowntimePage />,
  },
  [AppRoutes.NOT_FOUND]: {
    path: '*',
    element: <div>Страница не найдена</div>,
  },
};

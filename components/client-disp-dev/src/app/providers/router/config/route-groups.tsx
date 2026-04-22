import { type AppRouteType, AppRoutes, isAppRoute } from '@/shared/routes/router';

import { RouteWrapper } from '../ui/RouteWrapper';

import { routeConfig } from './route-config';

const excludedFromMainLayout = new Set<AppRouteType>([
  AppRoutes.LEARNING,
  AppRoutes.MAIN,
  AppRoutes.VGOK,
  AppRoutes.NOT_FOUND,
]);

export const appRoutes = Object.entries(routeConfig)
  .filter(([key]) => isAppRoute(key) && !excludedFromMainLayout.has(key))
  .map(([, route]) => ({
    path: route.path,
    element: <RouteWrapper route={route} />,
  }));

const upcomingRouteKeys = new Set<AppRouteType>([AppRoutes.LEARNING, AppRoutes.VGOK]);

export const upcomingRoutes = Object.entries(routeConfig)
  .filter(([key]) => isAppRoute(key) && upcomingRouteKeys.has(key))
  .map(([, route]) => ({
    path: route.path,
    element: <RouteWrapper route={route} />,
  }));

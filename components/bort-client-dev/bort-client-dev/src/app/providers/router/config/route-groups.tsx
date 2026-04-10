import { type AppRouteType, AppRoutes, isAppRoute } from '@/shared/routes/router';

import { RouteWrapper } from '../ui/RouteWrapper';

import { routeConfig } from './route-config';

const excludedFromProtectedRoutes = new Set<AppRouteType>([AppRoutes.NOT_FOUND, AppRoutes.LOGIN]);

/** Маршруты под AuthGuard (без логина и 404). */
export const appRoutes = Object.entries(routeConfig)
  .filter(([key]) => isAppRoute(key) && !excludedFromProtectedRoutes.has(key))
  .map(([, route]) => ({
    path: route.path,
    element: <RouteWrapper route={route} />,
  }));

/** Страница входа — вне AuthGuard. */
export const loginRoute = {
  path: routeConfig[AppRoutes.LOGIN].path,
  element: <RouteWrapper route={routeConfig[AppRoutes.LOGIN]} />,
};

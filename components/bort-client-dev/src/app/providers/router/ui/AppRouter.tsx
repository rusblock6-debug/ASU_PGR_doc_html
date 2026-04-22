import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';

import { AppRoutes as RouteKeys, getRouteMain } from '@/shared/routes/router';

import { routeConfig } from '../config/route-config';
import { appRoutes, loginRoute } from '../config/route-groups';

import { AuthGuard } from './AuthGuard';
import KioskLayoutWrapper from './KioskLayoutWrapper';
import { RouteWrapper } from './RouteWrapper';

/** Конфигурация маршрутизации приложения. */
const appRouter = createBrowserRouter([
  {
    element: <KioskLayoutWrapper />,
    children: [
      loginRoute,
      {
        element: <AuthGuard />,
        children: [
          {
            path: '/',
            element: (
              <Navigate
                to={getRouteMain()}
                replace
              />
            ),
          },
          ...appRoutes,
        ],
      },
    ],
  },
  {
    path: '*',
    element: <RouteWrapper route={routeConfig[RouteKeys.NOT_FOUND]} />,
  },
]);

/** Корневой компонент маршрутизации приложения. */
export function AppRouter() {
  return <RouterProvider router={appRouter} />;
}

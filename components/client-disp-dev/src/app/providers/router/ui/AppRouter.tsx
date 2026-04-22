import { createBrowserRouter, Outlet, RouterProvider } from 'react-router-dom';

import { EmptyLayout } from '@/shared/layouts/EmptyLayout';
import { AppRoutes as RouteKeys } from '@/shared/routes/router';

import { routeConfig } from '../config/route-config';
import { appRoutes, upcomingRoutes } from '../config/route-groups';

import { MainLayoutWrapper } from './MainLayoutWrapper';
import { RouteWrapper } from './RouteWrapper';

/** Конфигурация маршрутизации приложения. */
const appRouter = createBrowserRouter([
  // Маркетинговая страница (главная) без /app
  {
    path: routeConfig[RouteKeys.MAIN].path,
    element: <RouteWrapper route={routeConfig[RouteKeys.MAIN]} />,
  },
  // Страницы «Скоро тут будет…» используется на маркетинговой странице
  {
    element: <EmptyLayout content={<Outlet />} />,
    children: upcomingRoutes,
  },
  // Страницы приложения /app/*
  {
    element: <MainLayoutWrapper />,
    children: appRoutes,
  },
  // 404
  {
    path: '*',
    element: <RouteWrapper route={routeConfig[RouteKeys.NOT_FOUND]} />,
  },
]);

/** Корневой компонент маршрутизации приложения. */
export function AppRouter() {
  return <RouterProvider router={appRouter} />;
}

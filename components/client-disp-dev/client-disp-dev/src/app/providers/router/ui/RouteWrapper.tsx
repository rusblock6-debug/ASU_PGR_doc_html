import { Suspense } from 'react';

import type { AppRoutesProps } from '../config/route-config';

import { RequireAuth } from './RequireAuth';

/** Обёртка для маршрута с поддержкой ленивой загрузки и проверки прав доступа. */
export function RouteWrapper({ route }: { readonly route: AppRoutesProps }) {
  const element = <Suspense fallback={<p>Загрузка</p>}>{route.element}</Suspense>;
  return route.authOnly ? <RequireAuth roles={route.roles}>{element}</RequireAuth> : element;
}

import { Suspense } from 'react';

import type { AppRoutesProps } from '../config/route-config';

/** Обёртка для маршрута с поддержкой ленивой загрузки. */
export function RouteWrapper({ route }: { readonly route: AppRoutesProps }) {
  return <Suspense fallback={<p>Загрузка</p>}>{route.element}</Suspense>;
}

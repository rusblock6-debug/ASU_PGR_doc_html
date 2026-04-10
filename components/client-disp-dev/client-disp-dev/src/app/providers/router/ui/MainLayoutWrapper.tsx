import { matchPath, Outlet, useLocation } from 'react-router-dom';

import { AppHeader } from '@/widgets/app-header';
import { AppSidebar } from '@/widgets/app-sidebar';

import { MainLayout } from '@/shared/layouts/MainLayout';
import { cn } from '@/shared/lib/classnames-utils';
import { getRouteWorkspace } from '@/shared/routes/router';

import { RequireAuth } from './RequireAuth';

/**
 * Обёртка для основного макета приложения.
 *
 * Компонент обеспечивает:
 * - Защиту маршрутов через RequireAuth
 * - Специальные стили для рабочей области /workspace
 * - Рендеринг основного макета с сайдбаром, хедером и контентом
 */
export function MainLayoutWrapper() {
  const location = useLocation();
  const isWorkspacePage = matchPath(getRouteWorkspace(), location.pathname);

  return (
    <RequireAuth>
      <MainLayout
        className={cn({ 'workspace-page': isWorkspacePage })}
        sidebar={<AppSidebar />}
        header={<AppHeader />}
        content={<Outlet />}
      />
    </RequireAuth>
  );
}

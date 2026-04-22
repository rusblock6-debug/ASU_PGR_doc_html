import type { RouteProps } from 'react-router-dom';

import { AppPage } from '@/pages/app';
import { CargoPage } from '@/pages/cargo';
import { MapPage as NewMapPage } from '@/pages/dispatch-map';
import { DispatcherReportPage } from '@/pages/dispatchers-report';
import { EquipmentPage } from '@/pages/equipment';
import { FleetControlPage } from '@/pages/fleet-control';
import { ForbiddenPage } from '@/pages/forbidden';
import { HorizonsPage } from '@/pages/horizons';
import { LearningPage } from '@/pages/learning';
import { MainPage } from '@/pages/main';
import { MapPage } from '@/pages/map';
import { NotFoundPage } from '@/pages/not-found';
import { PlacesPage } from '@/pages/places';
import { RolesPage } from '@/pages/roles';
import { SectionsPage } from '@/pages/sections';
import { SettingsPage } from '@/pages/settings';
import { StaffPage } from '@/pages/staff';
import { StatusesPage } from '@/pages/statuses';
import { TagsPage } from '@/pages/tags';
import { TimeMapPage } from '@/pages/time-map';
import { TripEditorPage } from '@/pages/trip-editor';
import { VGOKPage } from '@/pages/vgok';
import { WorkOrderPage } from '@/pages/work-order';
import { WorkTimeMapPage } from '@/pages/work-time-map';
import { WorkspacePage } from '@/pages/workspace';

import { getRoutePermission } from '@/shared/routes/route-permissions';
import {
  type AppRouteType,
  AppRoutes,
  getRouteApp,
  getRouteDispatchersReport,
  getRouteEquipment,
  getRouteFleetControl,
  getRouteForbidden,
  getRouteHorizons,
  getRouteLearning,
  getRouteMain,
  getRouteDispatchMap,
  getRouteMap,
  getRoutePlaces,
  getRouteSections,
  getRouteSettings,
  getRouteStatuses,
  getRouteTimeMap,
  getRouteTripEditor,
  getRouteVGOK,
  getRouteWorkOrder,
  getRouteWorkspace,
  getRouteWorkTimeMap,
  getRouteTags,
  getRouteCargo,
  getRouteRoles,
  getRouteStaff,
} from '@/shared/routes/router';

/**
 * Расширенные props для конфигурации роутов (доступ + роли).
 *
 * permission — обязательное поле. Если забыть — ошибка компиляции. Используй getRoutePermission(AppRoutes.X).
 */
export type AppRoutesProps = RouteProps & {
  /** Имя разрешения из RolePermission.name. undefined = публичный роут (доступен всем). */
  readonly permission?: string;
};

/**
 * Конфигурация роутов приложения.
 */
export const routeConfig: Record<AppRouteType, AppRoutesProps> = {
  [AppRoutes.MAIN]: {
    path: getRouteMain(),
    element: <MainPage />,
    permission: getRoutePermission(AppRoutes.MAIN),
  },
  [AppRoutes.APP]: {
    path: getRouteApp(),
    element: <AppPage />,
    permission: getRoutePermission(AppRoutes.APP),
  },
  [AppRoutes.WORKSPACE]: {
    path: getRouteWorkspace(),
    element: <WorkspacePage />,
    permission: getRoutePermission(AppRoutes.WORKSPACE),
  },
  [AppRoutes.FLEET_CONTROL]: {
    path: getRouteFleetControl(),
    element: <FleetControlPage />,
    permission: getRoutePermission(AppRoutes.FLEET_CONTROL),
  },
  [AppRoutes.TIME_MAP]: {
    path: getRouteTimeMap(),
    element: <TimeMapPage />,
    permission: getRoutePermission(AppRoutes.TIME_MAP),
  },
  [AppRoutes.WORK_ORDER]: {
    path: getRouteWorkOrder(),
    element: <WorkOrderPage />,
    permission: getRoutePermission(AppRoutes.WORK_ORDER),
  },
  [AppRoutes.DISPATCHERS_REPORT]: {
    path: getRouteDispatchersReport(),
    element: <DispatcherReportPage />,
    permission: getRoutePermission(AppRoutes.DISPATCHERS_REPORT),
  },
  [AppRoutes.TRIP_EDITOR]: {
    path: getRouteTripEditor(),
    element: <TripEditorPage />,
    permission: getRoutePermission(AppRoutes.TRIP_EDITOR),
  },
  [AppRoutes.EQUIPMENT]: {
    path: getRouteEquipment(),
    element: <EquipmentPage />,
    permission: getRoutePermission(AppRoutes.EQUIPMENT),
  },
  [AppRoutes.PLACES]: {
    path: getRoutePlaces(),
    element: <PlacesPage />,
    permission: getRoutePermission(AppRoutes.PLACES),
  },
  [AppRoutes.TAGS]: {
    path: getRouteTags(),
    element: <TagsPage />,
    permission: getRoutePermission(AppRoutes.TAGS),
  },
  [AppRoutes.CARGO]: {
    path: getRouteCargo(),
    element: <CargoPage />,
    permission: getRoutePermission(AppRoutes.CARGO),
  },
  [AppRoutes.HORIZONS]: {
    path: getRouteHorizons(),
    element: <HorizonsPage />,
    permission: getRoutePermission(AppRoutes.HORIZONS),
  },
  [AppRoutes.STATUSES]: {
    path: getRouteStatuses(),
    element: <StatusesPage />,
    permission: getRoutePermission(AppRoutes.STATUSES),
  },
  [AppRoutes.SECTIONS]: {
    path: getRouteSections(),
    element: <SectionsPage />,
    permission: getRoutePermission(AppRoutes.SECTIONS),
  },
  [AppRoutes.DISPATCH_MAP]: {
    path: getRouteDispatchMap(),
    element: <NewMapPage />,
    permission: getRoutePermission(AppRoutes.DISPATCH_MAP),
  },
  [AppRoutes.MAP]: {
    path: getRouteMap(),
    element: <MapPage />,
    permission: getRoutePermission(AppRoutes.MAP),
  },
  [AppRoutes.WORK_TIME_MAP]: {
    path: getRouteWorkTimeMap(),
    element: <WorkTimeMapPage />,
    permission: getRoutePermission(AppRoutes.WORK_TIME_MAP),
  },
  [AppRoutes.ROLES]: {
    path: getRouteRoles(),
    element: <RolesPage />,
    permission: getRoutePermission(AppRoutes.ROLES),
  },
  [AppRoutes.STAFF]: {
    path: getRouteStaff(),
    element: <StaffPage />,
    permission: getRoutePermission(AppRoutes.STAFF),
  },
  [AppRoutes.LEARNING]: {
    path: getRouteLearning(),
    element: <LearningPage />,
    permission: getRoutePermission(AppRoutes.LEARNING),
  },
  [AppRoutes.VGOK]: {
    path: getRouteVGOK(),
    element: <VGOKPage />,
    permission: getRoutePermission(AppRoutes.VGOK),
  },
  [AppRoutes.SETTINGS]: {
    path: getRouteSettings(':id'),
    element: <SettingsPage />,
    permission: getRoutePermission(AppRoutes.SETTINGS),
  },
  [AppRoutes.FORBIDDEN]: {
    path: getRouteForbidden(),
    element: <ForbiddenPage />,
    permission: getRoutePermission(AppRoutes.FORBIDDEN),
  },
  [AppRoutes.NOT_FOUND]: {
    path: '*',
    element: <NotFoundPage />,
    permission: getRoutePermission(AppRoutes.NOT_FOUND),
  },
};

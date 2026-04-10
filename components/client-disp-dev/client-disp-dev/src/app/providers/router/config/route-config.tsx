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

import { UserRole, type UserRoleType } from '@/entities/user';

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

export type AppRoutesProps = RouteProps & {
  authOnly?: boolean;
  roles?: UserRoleType[];
};

export const routeConfig: Record<AppRouteType, AppRoutesProps> = {
  [AppRoutes.MAIN]: {
    path: getRouteMain(),
    element: <MainPage />,
  },
  [AppRoutes.APP]: {
    path: getRouteApp(),
    element: <AppPage />,
  },
  [AppRoutes.WORKSPACE]: {
    path: getRouteWorkspace(),
    element: <WorkspacePage />,
  },
  [AppRoutes.FLEET_CONTROL]: {
    path: getRouteFleetControl(),
    element: <FleetControlPage />,
  },
  [AppRoutes.TIME_MAP]: {
    path: getRouteTimeMap(),
    element: <TimeMapPage />,
  },
  [AppRoutes.WORK_ORDER]: {
    path: getRouteWorkOrder(),
    element: <WorkOrderPage />,
  },
  [AppRoutes.DISPATCHERS_REPORT]: {
    path: getRouteDispatchersReport(),
    element: <DispatcherReportPage />,
  },
  [AppRoutes.TRIP_EDITOR]: {
    path: getRouteTripEditor(),
    element: <TripEditorPage />,
  },
  [AppRoutes.EQUIPMENT]: {
    path: getRouteEquipment(),
    element: <EquipmentPage />,
  },
  [AppRoutes.PLACES]: {
    path: getRoutePlaces(),
    element: <PlacesPage />,
  },
  [AppRoutes.TAGS]: {
    path: getRouteTags(),
    element: <TagsPage />,
  },
  [AppRoutes.CARGO]: {
    path: getRouteCargo(),
    element: <CargoPage />,
  },
  [AppRoutes.HORIZONS]: {
    path: getRouteHorizons(),
    element: <HorizonsPage />,
  },
  [AppRoutes.STATUSES]: {
    path: getRouteStatuses(),
    element: <StatusesPage />,
  },
  [AppRoutes.SECTIONS]: {
    path: getRouteSections(),
    element: <SectionsPage />,
  },
  [AppRoutes.DISPATCH_MAP]: {
    path: getRouteDispatchMap(),
    element: <NewMapPage />,
  },
  [AppRoutes.MAP]: {
    path: getRouteMap(),
    element: <MapPage />,
  },
  [AppRoutes.WORK_TIME_MAP]: {
    path: getRouteWorkTimeMap(),
    element: <WorkTimeMapPage />,
  },
  [AppRoutes.ROLES]: {
    path: getRouteRoles(),
    element: <RolesPage />,
  },
  [AppRoutes.STAFF]: {
    path: getRouteStaff(),
    element: <StaffPage />,
  },
  [AppRoutes.LEARNING]: {
    path: getRouteLearning(),
    element: <LearningPage />,
  },
  [AppRoutes.VGOK]: {
    path: getRouteVGOK(),
    element: <VGOKPage />,
  },
  [AppRoutes.SETTINGS]: {
    path: getRouteSettings(':id'),
    element: <SettingsPage />,
    authOnly: true,
    roles: [UserRole.ADMIN],
  },
  [AppRoutes.FORBIDDEN]: {
    path: getRouteForbidden(),
    element: <ForbiddenPage />,
  },
  // last
  [AppRoutes.NOT_FOUND]: {
    path: '*',
    element: <NotFoundPage />,
  },
};

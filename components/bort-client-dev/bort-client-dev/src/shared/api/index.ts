export { rtkApi } from './rtk-api';

import './endpoints/shift-tasks/shift-tasks-rtk';
import './endpoints/event-log/event-log-rtk';
import './endpoints/vehicles/vehicles-rtk';
import './endpoints/tasks/tasks-rtk';
import './endpoints/vehicle-state/vehicle-state-rtk';
import './endpoints/tags/tags-rtk';

export type {
  ActiveTaskResponse,
  PaginatedResponse,
  RouteTaskResponse,
  ShiftTaskResponse,
  TripStatusRouteEnum,
} from './types/trip-service';
export { useGetShiftTaskByIdQuery, useGetShiftTasksQuery, useLazyGetShiftTaskByIdQuery } from './endpoints/shift-tasks';
export {
  useGetAvailableStatesQuery,
  useGetVehicleStateQuery,
  useSetVehicleStateTransitionMutation,
} from './endpoints/vehicle-state';
export {
  useActivateRouteTaskMutation,
  useCancelRouteTaskMutation,
  useClearActiveTaskMutation,
  useCompleteActiveTripMutation,
  useGetActiveTaskQuery,
  useGetRouteTaskByIdQuery,
  useGetRouteTasksQuery,
  useUpdateRouteTaskMutation,
} from './endpoints/tasks';
export type { SubscribeShiftTasksSseOptions } from './sse/shift-tasks-sse';
export { subscribeShiftTasksSse } from './sse/shift-tasks-sse';
export { useGetVehicleByIdQuery } from './endpoints/vehicles';
export type { VehicleResponse } from './endpoints/vehicles';
export { useGetCurrentShiftStatsQuery } from './endpoints/event-log';
export type { CurrentShiftStatsResponse } from './types/current-shift-stats';

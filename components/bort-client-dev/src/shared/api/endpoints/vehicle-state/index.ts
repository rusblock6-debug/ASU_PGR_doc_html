export {
  patchVehicleStateSnapshot,
  selectLocationPlaceName,
  selectLocationTagName,
  selectStateChangedAt,
  selectVehicleState,
  selectWeightValue,
  selectWifiConnected,
  useGetAvailableStatesQuery,
  useGetVehicleStateQuery,
  useSetVehicleStateTransitionMutation,
  useSubscribeVehicleEventsStreamQuery,
} from './vehicle-state-rtk';
export type { AvailableStateItem, VehicleStateResponse, VehicleStateTransitionBody } from './types';

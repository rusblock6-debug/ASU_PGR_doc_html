export {
  vehicleRtkApi,
  useGetAllVehiclesQuery,
  useGetVehiclesInfiniteQuery,
  useGetVehiclePlacesQuery,
  useGetVehicleStateQuery,
  useGetVehiclePopupQuery,
  useGetVehicleByIdQuery,
  useCreateVehicleMutation,
  useUpdateVehicleMutation,
  useDeleteVehicleMutation,
} from './vehicles-rtk';

export type {
  CreateVehicleRequest,
  UpdateVehicleRequest,
  Vehicle,
  VehiclePlaceItem,
  VehiclePlacesResponse,
  VehiclePopupResponse,
  VehicleStateItem,
  VehicleStateResponse,
  VehiclesResponse,
  VehicleStatus,
  VehicleType,
  VehiclesQueryArg,
} from './types';

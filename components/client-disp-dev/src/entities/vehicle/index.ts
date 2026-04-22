export {
  vehicleTypeOptions,
  VehicleTypeLabels,
  VEHICLE_TYPES,
  DEFAULT_VEHICLE_TYPE,
  getVehicleTypeOrangeIcon,
  getVehicleTypeDisplayName,
  type SelectableVehicleType,
} from './model/constants';
export {
  selectAllVehicleIds,
  selectAllVehicles,
  selectVehicleById,
  selectVehicleStatus,
  selectVehicleSpecs,
} from './model/selectors';
export { generateVehicleName } from './lib/generate-vehicle-name';

export { VehicleTypeIcon } from './ui/VehicleTypeIcon';
export { VehicleMarker } from './ui/VehicleMarker';

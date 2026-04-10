import { vehicleModelsHandlers } from './vehicle-models';
import { vehiclesHandlers } from './vehicles';

export const handlers = [...vehiclesHandlers, ...vehicleModelsHandlers];

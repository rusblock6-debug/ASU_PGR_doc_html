import { faker } from '@faker-js/faker';

import type { Vehicle, VehicleStatus, VehicleType } from '@/shared/api/endpoints/vehicles';

import { generateVehicleModel } from './vehicle-model';

const VEHICLE_TYPES: VehicleType[] = ['shas', 'pdm'];

let vehicleIdCounter = 1;

export function generateVehicle(overrides?: Partial<Vehicle>): Vehicle {
  const now = new Date().toISOString();
  const vehicleType = faker.helpers.arrayElement(VEHICLE_TYPES);
  const hasModel = faker.datatype.boolean();
  const model = hasModel ? generateVehicleModel() : null;

  return {
    id: vehicleIdCounter++,
    enterprise_id: 1,
    vehicle_type: vehicleType,
    name: `${vehicleType.toUpperCase()}-${faker.number.int({ min: 100, max: 999 })}`,
    model_id: model?.id ?? null,
    model,
    serial_number: faker.string.alphanumeric({ length: 10, casing: 'upper' }),
    registration_number: `${faker.string.alpha({ length: 1, casing: 'upper' })}${faker.number.int({ min: 100, max: 999 })}${faker.string.alpha({ length: 2, casing: 'upper' })}`,
    status: faker.helpers.weightedArrayElement([
      { value: 'active' as VehicleStatus, weight: 7 },
      { value: 'maintenance' as VehicleStatus, weight: 1 },
      { value: 'repair' as VehicleStatus, weight: 1 },
      { value: 'inactive' as VehicleStatus, weight: 1 },
    ]),
    is_active: faker.datatype.boolean({ probability: 0.85 }),
    active_from: faker.date.past({ years: 1 }).toISOString(),
    active_to:
      faker.helpers.maybe(() => faker.date.future({ years: 1 }).toISOString(), {
        probability: 0.3,
      }) ?? null,
    created_at: faker.date.past({ years: 2 }).toISOString(),
    updated_at: now,
    ...overrides,
  };
}

export function generateVehicles(count: number): Vehicle[] {
  return Array.from({ length: count }, () => generateVehicle());
}

export function resetVehicleIdCounter(): void {
  vehicleIdCounter = 1;
}

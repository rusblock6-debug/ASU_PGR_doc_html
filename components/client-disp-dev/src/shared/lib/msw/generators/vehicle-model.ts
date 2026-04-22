import { faker } from '@faker-js/faker';

import type { EquipmentModel } from '@/shared/api/endpoints/equipment-models';

const MODEL_NAMES = [
  'БелАЗ 75131',
  'БелАЗ 75306',
  'БелАЗ 75710',
  'CAT 777G',
  'CAT 785D',
  'CAT 793F',
  'Komatsu HD785-7',
  'Komatsu 930E-4',
  'Hitachi EH3500AC-3',
  'Liebherr T 264',
  'Liebherr T 284',
  'Terex MT 4400',
];

let modelIdCounter = 1;

export function generateVehicleModel(overrides?: Partial<EquipmentModel>): EquipmentModel {
  const now = new Date().toISOString();

  return {
    id: modelIdCounter++,
    name: faker.helpers.arrayElement(MODEL_NAMES),
    max_speed: faker.number.int({ min: 40, max: 65 }),
    tank_volume: faker.number.int({ min: 2000, max: 5000 }),
    load_capacity_tons: faker.number.int({ min: 100, max: 450 }),
    volume_m3: faker.number.int({ min: 50, max: 200 }),
    created_at: faker.date.past({ years: 2 }).toISOString(),
    updated_at: now,
    ...overrides,
  };
}

export function generateVehicleModels(count: number): EquipmentModel[] {
  return Array.from({ length: count }, () => generateVehicleModel());
}

export function resetVehicleModelIdCounter(): void {
  modelIdCounter = 1;
}

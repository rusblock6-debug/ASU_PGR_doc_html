import { createSelector } from '@reduxjs/toolkit';

import { vehicleRtkApi } from '@/shared/api/endpoints/vehicles';

/**
 * Результат запроса всех транспортных средств из RTK Query кеша.
 * Единый экземпляр селектора — переиспользуется во всех vehicle-селекторах.
 */
const selectAllVehiclesResult = vehicleRtkApi.endpoints.getAllVehicles.select();

/**
 * Возвращает ID всех транспортных средств.
 */
export const selectAllVehicleIds = createSelector([selectAllVehiclesResult], (result) => result.data?.ids || []);

/**
 * Возвращает все транспортные средства.
 */
export const selectAllVehicles = createSelector([selectAllVehiclesResult], (result) => {
  if (!result.data) return [];
  return Object.values(result.data.entities);
});

/**
 * Возвращает транспортное средство.
 */
export const selectVehicleById = createSelector(
  [selectAllVehiclesResult, (_state: RootState, vehicleId: number) => vehicleId],
  (vehiclesResult, vehicleId) => vehiclesResult.data?.entities[vehicleId],
);

/**
 * Возвращает характеристики машины (грузоподъёмность, объём кузова/ковша).
 */
export const selectVehicleSpecs = createSelector([selectVehicleById], (vehicle) => ({
  loadCapacity: vehicle?.model?.load_capacity_tons ?? null,
  volumeM3: vehicle?.model?.volume_m3 ?? null,
}));

/**
 * Возвращает статус транспортного средства.
 */
export const selectVehicleStatus = createSelector([selectVehicleById], (vehicle) => vehicle?.status ?? null);

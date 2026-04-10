/**
 * ID борта / техники.
 * Используется для фильтрации смен и API-запросов.
 */
const rawVehicleId = import.meta.env.VITE_VEHICLE_ID;
const parsedVehicleId = rawVehicleId != null ? Number(String(rawVehicleId).trim()) : Number.NaN;

export const VEHICLE_ID_NUM = Number.isFinite(parsedVehicleId) ? parsedVehicleId : 4;

/** Строковое представление ID техники для query-параметров API. */
export const VEHICLE_ID_STR = String(VEHICLE_ID_NUM);

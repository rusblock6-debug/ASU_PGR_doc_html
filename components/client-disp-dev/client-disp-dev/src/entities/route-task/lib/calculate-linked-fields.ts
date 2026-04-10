import { roundToFixed } from '@/shared/lib/format-number';
import { hasValue } from '@/shared/lib/has-value';

/**
 * Параметры для расчёта связанных полей.
 */
interface CalculationParams {
  /** Плотность груза (ρ), т/м³ */
  readonly density: number;
  /** Грузоподъёмность ТС (Cₜ), тонн */
  readonly loadCapacity: number;
  /** Объём кузова/ковша ТС (Cᵥ), м³ */
  readonly volumeM3: number;
}

/**
 * Результат расчёта зависимых полей.
 */
interface CalculatedFields {
  /** Объем груза. */
  readonly volume?: number | null;
  /** Вес груза. */
  readonly weight?: number | null;
  /** Количество рейсов. */
  readonly plannedTripsCount?: number | null;
}

/**
 * Расчёт веса и рейсов при вводе объёма.
 *
 * Формулы:
 * - M = V × ρ (вес = объём × плотность груза)
 * - R = max(round(M / Cₜ), round(V / Cᵥ)) (рейсы = максимум из ограничений по весу и по объёму)
 *
 * Где:
 * - V — объём груза, м³
 * - M — масса груза, тонн
 * - ρ — плотность груза, т/м³
 * - Cₜ — грузоподъёмность ТС, тонн
 * - Cᵥ — объём кузова/ковша ТС, м³
 * - R — количество рейсов
 */
export function calculateFromVolume(volume: number | null, params: CalculationParams): CalculatedFields {
  if (!hasValue(volume)) {
    return { weight: null, plannedTripsCount: null };
  }

  const { density, loadCapacity, volumeM3 } = params;

  const weight = roundToFixed(volume * density);
  const tripsByWeight = Math.ceil(weight / loadCapacity);
  const tripsByVolume = Math.ceil(volume / volumeM3);
  const plannedTripsCount = Math.max(tripsByWeight, tripsByVolume);

  return { weight, plannedTripsCount };
}

/**
 * Расчёт объёма и рейсов при вводе веса.
 *
 * Формулы:
 * - V = M / ρ (объём = вес / плотность груза)
 * - R = max(round(M / Cₜ), round(V / Cᵥ)) (рейсы = максимум из ограничений по весу и по объёму)
 *
 * Где:
 * - M — масса груза, тонн
 * - V — объём груза, м³
 * - ρ — плотность груза, т/м³
 * - Cₜ — грузоподъёмность ТС, тонн
 * - Cᵥ — объём кузова/ковша ТС, м³
 * - R — количество рейсов
 */
export function calculateFromWeight(weight: number | null, params: CalculationParams): CalculatedFields {
  if (!hasValue(weight)) {
    return { volume: null, plannedTripsCount: null };
  }

  const { density, loadCapacity, volumeM3 } = params;

  const volume = roundToFixed(weight / density);
  const tripsByWeight = Math.ceil(weight / loadCapacity);
  const tripsByVolume = Math.ceil(volume / volumeM3);
  const plannedTripsCount = Math.max(tripsByWeight, tripsByVolume);

  return { volume, plannedTripsCount };
}

/**
 * Расчёт веса и объёма при вводе рейсов.
 *
 * Эффективная загрузка за рейс ограничена весом или объёмом:
 * - Mᵣ = min(Cₜ, Cᵥ × ρ) (эффективный вес за рейс)
 * - Vᵣ = min(Cₜ / ρ, Cᵥ) (эффективный объём за рейс)
 *
 * Формулы:
 * - M = R × Mᵣ (вес = рейсы × эффективный вес за рейс)
 * - V = R × Vᵣ (объём = рейсы × эффективный объём за рейс)
 *
 * Где:
 * - R — количество рейсов
 * - Cₜ — грузоподъёмность ТС, тонн
 * - Cᵥ — объём кузова/ковша ТС, м³
 * - ρ — плотность груза, т/м³
 * - M — масса груза, тонн
 * - V — объём груза, м³
 */
export function calculateFromTrips(trips: number | null, params: CalculationParams): CalculatedFields {
  if (!hasValue(trips)) {
    return { volume: null, weight: null };
  }

  const { density, loadCapacity, volumeM3 } = params;

  const weightPerTrip = Math.min(loadCapacity, volumeM3 * density);
  const volumePerTrip = Math.min(loadCapacity / density, volumeM3);

  const weight = roundToFixed(trips * weightPerTrip);
  const volume = roundToFixed(trips * volumePerTrip);

  return { volume, weight };
}

import { hasValue } from '@/shared/lib/has-value';

import type { BlockReasonValue, TaskBlockState } from './types';

/**
 * Причины блокировки задания.
 */
export const BlockReason = {
  /** Не выбрано место погрузки. */
  NO_PLACE_START: 'no_place_start',
  /** Для места погрузки не указан тип груза. */
  NO_CARGO: 'no_cargo',
  /** Для типа груза не указана плотность. */
  NO_DENSITY: 'no_density',
  /** Для техники не указаны грузоподъёмность или объём кузова. */
  NO_VEHICLE_SPECS: 'no_vehicle_specs',
  /** Не заполнены обязательные поля. */
  REQUIRED_FIELDS: 'required_fields',
} as const;

/**
 * Сообщения об ошибках для каждой причины блокировки.
 */
const BLOCK_REASON_MESSAGES: Record<BlockReasonValue, string> = {
  [BlockReason.NO_PLACE_START]: 'Сначала выберите место погрузки.',
  [BlockReason.NO_CARGO]: 'У места погрузки не указан вид груза. Выберите другое место погрузки.',
  [BlockReason.NO_DENSITY]: 'Для типа груза у места погрузки не указана плотность.',
  [BlockReason.NO_VEHICLE_SPECS]: 'Для техники не указаны грузоподъёмность и/или объём кузова.',
  [BlockReason.REQUIRED_FIELDS]: 'Не все поля заполнены.',
} as const;

/**
 * Возвращает сообщение об ошибке для задания на основе состояния блокировки.
 */
export function getBlockReasonMessage(blockState: TaskBlockState | null) {
  if (!hasValue(blockState)) return null;
  return BLOCK_REASON_MESSAGES[blockState.reason];
}

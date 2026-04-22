import { hasValue } from '@/shared/lib/has-value';

import type { WarningReasonValue } from './types';

/**
 * Причины предупреждений для задания.
 */
export const RouteTaskWarningReason = {
  /** Несоответствие видов груза. */
  MISMATCH_TYPE_CARGO: 'mismatch_types_cargo',
} as const;

/**
 * Сообщения о предупреждениях для каждой причины предупреждения.
 */
const ROUTE_TASK_WARNING_REASON_MESSAGES: Record<WarningReasonValue, string> = {
  [RouteTaskWarningReason.MISMATCH_TYPE_CARGO]:
    'Вид груза в месте погрузки не соответствует виду груза в месте разгрузки.',
} as const;

/**
 * Возвращает сообщение о предупреждении для задания на основе состояния предупреждения.
 */
export function getWarningReasonMessage(warningReason?: WarningReasonValue | null) {
  if (!hasValue(warningReason)) return null;
  return ROUTE_TASK_WARNING_REASON_MESSAGES[warningReason];
}

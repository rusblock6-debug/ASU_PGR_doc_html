import { formatNumber } from '@/shared/lib/format-number';
import { formatInTimezone } from '@/shared/lib/timezone';

import type { SelectValueType } from '../model/column-meta';
import { type ColumnDataType, ColumnDataTypes } from '../types';

const MSK_TIMEZONE = 'Europe/Moscow';

/**
 * Форматирует значение в зависимости от типа данных
 */
export function formatValue(value: unknown, dataType?: ColumnDataType): string {
  if (value === null || value === undefined) return '';

  switch (dataType) {
    case ColumnDataTypes.DATE:
      return formatDate(value);
    case ColumnDataTypes.DATETIME:
      return formatDateTime(value);
    case ColumnDataTypes.TIME:
      return formatTime(value);
    case ColumnDataTypes.NUMBER:
      return formatNumber(value);
    default:
      return String(value);
  }
}

/**
 * Преобразует строковое значение выпадающего списка в целевой тип {@link SelectValueType}.
 */
export function formatSelectValue(value: string | null, valueType: SelectValueType) {
  if (value === null) return null;

  if (valueType === 'number') {
    return Number(value);
  }

  if (valueType === 'boolean') {
    return value === 'true';
  }

  return value;
}

/**
 * Форматирует дату в формате DD.MM.YYYY (МСК таймзона)
 */
function formatDate(value: unknown): string {
  if (!value) return '';

  try {
    const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : (value as Date);
    if (isNaN(date.getTime())) return String(value);

    return formatInTimezone(date, MSK_TIMEZONE, 'dd.MM.yyyy');
  } catch {
    return String(value);
  }
}

/**
 * Форматирует дату и время в формате DD.MM.YYYY HH:mm (МСК таймзона)
 */
function formatDateTime(value: unknown): string {
  if (!value) return '';

  try {
    const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : (value as Date);
    if (isNaN(date.getTime())) return String(value);

    // Форматируем с минимальным расстоянием между датой и временем (используем неразрывный пробел)
    const formattedDate = formatInTimezone(date, MSK_TIMEZONE, 'dd.MM.yyyy');
    const formattedTime = formatInTimezone(date, MSK_TIMEZONE, 'HH:mm:ss');

    return `${formattedDate}\u00A0${formattedTime}`;
  } catch {
    return String(value);
  }
}

/**
 * Форматирует время в формате HH:mm (МСК таймзона)
 */
function formatTime(value: unknown): string {
  if (!value) return '';

  try {
    // Если это строка формата "HH:mm", возвращаем как есть
    if (typeof value === 'string' && /^\d{2}:\d{2}$/.test(value)) {
      return value;
    }

    const date = typeof value === 'string' || typeof value === 'number' ? new Date(value) : (value as Date);
    if (isNaN(date.getTime())) return String(value);

    return formatInTimezone(date, MSK_TIMEZONE, 'HH:mm');
  } catch {
    return String(value);
  }
}

import { format as dateFnsFormat, parse } from 'date-fns';
import { ru } from 'date-fns/locale';
import { formatInTimeZone, fromZonedTime, toZonedTime } from 'date-fns-tz';

export type DateType = Date | string | number;

/**
 * Функция форматирования для конкретной таймзоны.
 * Использовать когда таймзона известна заранее. По-умолчанию используйте хук useTimezone.
 * Ниже createTimezoneFormatter идут отдельные функции для использования там где нельзя применить хук.
 * Храните даты в UTC, преобразовывайте для отображения.
 *
 * Правильный порядок работы с датами
 * 1. ПОЛУЧЕНИЕ (API → Client):
 *    UTC → форматирование в таймзоне (функция toTimezone) → показ пользователю
 *
 * 2. ОТПРАВКА (Client → API):
 *    Ввод пользователя → парсинг в таймзоне (функция toTimezone) → перевод в UTC (функция toUTC) → отправка
 */
export function createTimezoneFormatter(timezone: string | undefined | null) {
  return {
    format: (date: DateType, formatStr?: string) => formatInTimezone(date, timezone, formatStr),

    formatDateTime: (date: DateType) => formatInTimezone(date, timezone, 'dd.MM.yyyy HH:mm:ss'),

    formatDate: (date: DateType) => formatInTimezone(date, timezone, 'dd.MM.yyyy'),

    formatTime: (date: DateType) => formatInTimezone(date, timezone, 'HH:mm:ss'),

    getNow: () => getNowInTimezone(timezone),

    getNowUTC: () => getNowInTimezoneAsUTC(timezone),

    toTimezone: (date: Date | string) => toTimezone(date, timezone),

    toUTC: (date: Date | string) => toUTC(date, timezone),

    /** Преобразует дату в UTC ISO строку с обнулёнными секундами (формат: 2025-12-02T20:53:00.000Z) */
    toUTCString: (date: Date | string) => normalizeISODateTime(toUTC(date, timezone)),

    toUTCStringWithSeconds: (date: Date | string) => normalizeISODateTimeWithSeconds(toUTC(date, timezone)),

    utcToDatetimeLocal: (utcString: string) => utcToDatetimeLocal(utcString, timezone),

    datetimeLocalToUTC: (datetimeLocal: string) => datetimeLocalToUTC(datetimeLocal, timezone),

    dateTimeInputsToUTC: (dateInput: string, timeInput: string) => dateTimeInputsToUTC(dateInput, timeInput, timezone),

    // Утилиты для работы с vis-timeline
    createLocalDateWithTimezoneValues: (date: Date | string) => createLocalDateWithTimezoneValues(date, timezone),
    localDateToUTC: (localDate: Date) => localDateWithTimezoneValuesToUTC(localDate, timezone),

    timezone,
  };
}

/**
 * Форматирует дату в указанной таймзоне
 * Если таймзона не указана, использует локальное время браузера
 */
export function formatInTimezone(date: DateType, timezone: string | undefined | null, formatStr = 'dd.MM.yyyy HH:mm') {
  if (!date) return '';

  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;

    if (timezone) {
      return formatInTimeZone(dateObj, timezone, formatStr, { locale: ru });
    }

    return dateFnsFormat(dateObj, formatStr, { locale: ru });
  } catch {
    return String(date);
  }
}

/**
 * Преобразует дату в указанную таймзону
 */
export function toTimezone(date: Date | string, timezone: string | undefined | null) {
  if (!timezone) {
    return typeof date === 'string' ? new Date(date) : date;
  }

  return toZonedTime(date, timezone);
}

/**
 * Получить текущую дату/время в указанной таймзоне
 */
export function getNowInTimezone(timezone: string | undefined | null) {
  if (!timezone) {
    return new Date();
  }

  return toZonedTime(new Date(), timezone);
}

/**
 * Преобразует дату из указанной таймзоны в UTC
 */
export function toUTC(date: Date | string, timezone: string | undefined | null) {
  if (!timezone) {
    return typeof date === 'string' ? new Date(date) : date;
  }

  return fromZonedTime(date, timezone);
}

/**
 * Преобразовать текущее время из таймзоны в UTC ISO строку
 */
export function getNowInTimezoneAsUTC(timezone: string | undefined | null) {
  const zonedTime = getNowInTimezone(timezone);

  if (!timezone) {
    return zonedTime.toISOString();
  }

  // Преобразуем обратно в UTC
  return fromZonedTime(zonedTime, timezone).toISOString();
}

/**
 * Преобразует UTC ISO строку в значение для <input type="datetime-local">
 *
 * @param utcString - UTC ISO строка (например "2025-10-24T05:00:00.000Z")
 * @param timezone - таймзона (например "Europe/Moscow")
 * @returns значение для input (например "2025-10-24T08:00")
 */
export function utcToDatetimeLocal(utcString: string, timezone: string | undefined | null) {
  if (!utcString || !timezone) return '';
  return formatInTimezone(utcString, timezone, "yyyy-MM-dd'T'HH:mm");
}

/**
 * Преобразует значение из <input type="datetime-local"> в UTC ISO строку
 *
 * @param datetimeLocal - значение из input (например "2025-10-24T08:00")
 * @param timezone - таймзона (например "Europe/Moscow")
 * @returns UTC ISO строка для отправки на сервер
 */
export function datetimeLocalToUTC(datetimeLocal: string, timezone: string | undefined | null) {
  if (!datetimeLocal || !timezone) return '';
  const localDate = parse(datetimeLocal, "yyyy-MM-dd'T'HH:mm", new Date());
  return toUTC(localDate, timezone).toISOString();
}

/**
 * Преобразует значения из <input type="date"> и <input type="time"> в UTC ISO строку
 *
 * @param dateInput - значение из date input (например "2025-10-24")
 * @param timeInput - значение из time input (например "08:30")
 * @param timezone - таймзона (например "Europe/Moscow")
 * @returns UTC ISO строка для отправки на сервер
 */
export function dateTimeInputsToUTC(dateInput: string, timeInput: string, timezone: string | undefined | null) {
  if (!dateInput || !timeInput || !timezone) return '';
  const datetimeLocal = `${dateInput}T${timeInput}`;
  const localDate = parse(datetimeLocal, "yyyy-MM-dd'T'HH:mm", new Date());
  return toUTC(localDate, timezone).toISOString();
}

/**
 * Создаёт локальный Date объект с московскими значениями времени (для vis-timeline)
 * Это «хак» для библиотек, которые не поддерживают таймзоны — создаём Date в локальной
 * системе браузера, но со значениями из указанной таймзоны
 *
 * @param date - Date объект (может быть в UTC или любой таймзоне)
 * @param timezone - таймзона, из которой нужно взять значения
 * @returns Date с локальными значениями из указанной таймзоны
 */
export function createLocalDateWithTimezoneValues(date: Date | string, timezone: string | undefined | null) {
  const dateObj = typeof date === 'string' ? new Date(date) : date;

  if (!timezone) {
    return dateObj;
  }

  // Получаем значения времени в указанной таймзоне
  const zonedDate = toZonedTime(dateObj, timezone);

  // Создаём локальный Date с этими значениями
  return new Date(
    zonedDate.getFullYear(),
    zonedDate.getMonth(),
    zonedDate.getDate(),
    zonedDate.getHours(),
    zonedDate.getMinutes(),
    zonedDate.getSeconds(),
    0,
  );
}

/**
 * Преобразует локальный Date с таймзон-специфичными значениями обратно в UTC
 * Обратная операция для createLocalDateWithTimezoneValues
 *
 * @param localDate - локальный Date объект с значениями из таймзоны
 * @param timezone - таймзона, в которой интерпретировать значения
 * @returns UTC Date
 */
export function localDateWithTimezoneValuesToUTC(localDate: Date, timezone: string | undefined | null) {
  if (!timezone) {
    return localDate;
  }

  // Создаём ISO строку из локальных значений Date
  const year = localDate.getFullYear();
  const month = String(localDate.getMonth() + 1).padStart(2, '0');
  const day = String(localDate.getDate()).padStart(2, '0');
  const hours = String(localDate.getHours()).padStart(2, '0');
  const minutes = String(localDate.getMinutes()).padStart(2, '0');
  const seconds = String(localDate.getSeconds()).padStart(2, '0');

  const isoString = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;

  // fromZonedTime интерпретирует эту строку как время в указанной таймзоне
  return fromZonedTime(isoString, timezone);
}

/**
 * Нормализует ISO дату, обнуляя секунды и миллисекунды.
 * «2025-12-02T20:53:42.012208Z» → «2025-12-02T20:53:00.000Z»
 */
export function normalizeISODateTime(value: Date | string) {
  const date = typeof value === 'string' ? new Date(value) : value;
  return formatInTimeZone(date, 'UTC', "yyyy-MM-dd'T'HH:mm:00.000'Z'");
}

/**
 * Нормализует ISO дату, обнуляя миллисекунды.
 * «2025-12-02T20:53:42.012208Z» → «2025-12-02T20:53:42.000Z»
 */
export function normalizeISODateTimeWithSeconds(value: Date | string) {
  const date = typeof value === 'string' ? new Date(value) : value;
  return formatInTimeZone(date, 'UTC', "yyyy-MM-dd'T'HH:mm:ss.000'Z'");
}
